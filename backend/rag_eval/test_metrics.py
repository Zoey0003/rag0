"""离线检查排序指标和预算，不访问模型接口或数据库。"""
import unittest
from unittest.mock import Mock

from rag_eval.common import fingerprint, retrieval_metrics, stats, validate_cases
from rag_eval.run import build_context


class MetricTests(unittest.TestCase):
    """验证指标边界、快照一致性和标注门槛。"""

    def test_ranking(self):
        """两块命中且首块在第二名，Recall=1、RR=0.5。"""
        self.assertEqual(retrieval_metrics(["x", "a", "b"], ["a", "b"]),
                         {"recall5": 1, "mrr5": .5, "hit5": 1})

    def test_cutoff_and_empty(self):
        """第五名之后不计分，无标注时不给虚假零分。"""
        self.assertEqual(retrieval_metrics(["1", "2", "3", "4", "5", "a"], ["a"])["mrr5"], 0)
        self.assertIsNone(retrieval_metrics([], [])["recall5"])
        self.assertEqual(retrieval_metrics(["a", "a"], ["a", "b"])["recall5"], .5)

    def test_snapshot(self):
        """读取顺序不影响指纹，但正文变化必须触发不同指纹。"""
        a = [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}]
        self.assertEqual(fingerprint(a), fingerprint(a[::-1]))
        self.assertNotEqual(fingerprint(a), fingerprint([{ "id": "1", "text": "changed"}]))

    def test_annotation_guard(self):
        """未标注题集不得进入正式实验。"""
        with self.assertRaises(ValueError):
            validate_cases([{"id": "q", "question": "测试", "relevant_chunk_ids": []}], [])

    def test_statistics_and_context(self):
        """确认 nearest-rank 分位数及实际正文预算。"""
        self.assertEqual(stats([1, 2, 3])["p95"], 3)
        self.assertIsNone(stats([])["mean"])
        contexts, _ = build_context([{"text": "字" * 20000}])
        self.assertEqual(len(contexts[0]), 16000)

    def test_retrieval_adapters(self):
        """模拟数据库返回，确认三种检索都保持 ID、正文和统一 Top 5 截断。"""
        from rag_eval.retrieval import Retriever

        obj = object.__new__(Retriever)
        obj.client = Mock()
        obj.embedding = Mock()
        obj.embedding.embed_query.return_value = [0.1] * 512
        obj.reranker = None
        hits = [{"id": i, "distance": 1.0, "entity": {"text": f"正文{i}"}} for i in range(8)]
        obj.client.search.return_value = [hits]
        obj.client.hybrid_search.return_value = [hits]
        for method in ["bm25", "bge", "hybrid"]:
            result = obj.search("测试问题", method)
            self.assertEqual(len(result["chunks"]), 5)
            self.assertEqual(result["chunks"][0]["id"], "0")
            self.assertGreaterEqual(result["retrieval_seconds"], 0)
        self.assertEqual(obj.embedding.embed_query.call_count, 2)

    def test_optional_reranker(self):
        """模拟重排，将高分末位块移到首位，并检查缺少模型时明确报错。"""
        from rag_eval.retrieval import Retriever

        obj = object.__new__(Retriever)
        obj.client = Mock()
        obj.embedding = Mock()
        obj.embedding.embed_query.return_value = [0.0] * 512
        obj.reranker = None
        with self.assertRaises(ValueError):
            obj.search("问题", "hybrid_rerank")
        obj.reranker = Mock()
        obj.reranker.predict.return_value = [0.1, 0.9]
        obj.client.hybrid_search.return_value = [[
            {"id": 1, "distance": .5, "entity": {"text": "A"}},
            {"id": 2, "distance": .4, "entity": {"text": "B"}},
        ]]
        self.assertEqual(obj.search("问题", "hybrid_rerank")["chunks"][0]["id"], "2")


if __name__ == "__main__":
    unittest.main()
