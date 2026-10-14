"""统一候选预算的 BM25、BGE、RRF 检索，以及可选本地重排序。"""
from time import perf_counter

from pymilvus import AnnSearchRequest, MilvusClient, RRFRanker

from rag_eval import config as cfg

FIELDS = ["text", "filename", "title", "source", "category"]
FILTER = 'category == "content"'
DENSE = {"metric_type": "IP", "params": {"ef": 64}}
SPARSE = {"metric_type": "BM25", "params": {}}


def normalize(row):
    """将数据库行转换成统一块结构，主键转字符串以兼容 JSON 标注。"""
    return {"id": str(row["id"]), **{field: row.get(field, "") for field in FIELDS}}


class Retriever:
    """一次加载检索资源，初始化耗时与请求耗时分开记录。"""

    def __init__(self, reranker_path=None):
        """连接现有集合并加载本地模型，绝不调用创建或删除集合方法。"""
        from langchain_huggingface import HuggingFaceEmbeddings

        self.client = MilvusClient(uri=cfg.URI)
        self.reranker = None
        try:
            self.client.load_collection(collection_name=cfg.COLLECTION)
            self.embedding = HuggingFaceEmbeddings(model_name=cfg.BGE_PATH,
                model_kwargs={"device": "cpu"}, encode_kwargs={"normalize_embeddings": True})
            if reranker_path:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder(reranker_path, device="cpu")
        except Exception:
            self.client.close()
            raise

    def close(self):
        """释放本实验创建的 Milvus 连接。"""
        self.client.close()

    def snapshot(self):
        """分页读取全部正文，供标注及实验前后指纹检查使用。"""
        iterator = self.client.query_iterator(collection_name=cfg.COLLECTION, batch_size=500,
            filter=FILTER, output_fields=["id", *FIELDS], consistency_level="Strong")
        chunks = []
        try:
            while True:
                rows = iterator.next()
                if not rows:
                    break
                chunks.extend(normalize(row) for row in rows)
        finally:
            iterator.close()
        return sorted(chunks, key=lambda c: c["id"])

    def search(self, question, method, limit=cfg.TOP_K):
        """计时编码、数据库请求、重排；混合请求内部含 RRF，不能独立计其耗时。"""
        if method not in [*cfg.METHODS, "hybrid_rerank"]:
            raise ValueError(f"未知方法：{method}")
        if method == "hybrid_rerank" and self.reranker is None:
            raise ValueError("hybrid_rerank 需要 --reranker 指定本地 CrossEncoder 模型")
        started = perf_counter()
        encoding_seconds = 0.0
        vector = None
        if method != "bm25":
            mark = perf_counter()
            vector = self.embedding.embed_query(question)
            encoding_seconds = perf_counter() - mark
        mark = perf_counter()
        if method in {"bm25", "bge"}:
            dense = method == "bge"
            hits = self.client.search(collection_name=cfg.COLLECTION,
                data=[vector if dense else question], anns_field="dense" if dense else "sparse",
                filter=FILTER, limit=cfg.CANDIDATES, search_params=DENSE if dense else SPARSE,
                output_fields=FIELDS, consistency_level="Strong")[0]
        else:
            requests = [
                AnnSearchRequest([vector], "dense", DENSE, cfg.CANDIDATES, expr=FILTER),
                AnnSearchRequest([question], "sparse", SPARSE, cfg.CANDIDATES, expr=FILTER),
            ]
            hits = self.client.hybrid_search(collection_name=cfg.COLLECTION, reqs=requests,
                ranker=RRFRanker(k=100), limit=cfg.CANDIDATES, output_fields=FIELDS,
                consistency_level="Strong")[0]
        database_seconds = perf_counter() - mark
        chunks = [{**normalize({"id": h["id"], **h["entity"]}), "score": float(h["distance"])} for h in hits]
        rerank_seconds = 0.0
        if method == "hybrid_rerank" and chunks:
            mark = perf_counter()
            scores = self.reranker.predict([(question, c["text"]) for c in chunks])
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = float(score)
            chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
            rerank_seconds = perf_counter() - mark
        return {"chunks": chunks[:limit], "encoding_seconds": encoding_seconds,
                "database_seconds": database_seconds, "rerank_seconds": rerank_seconds,
                "retrieval_seconds": perf_counter() - started}
