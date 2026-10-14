import json
from pathlib import Path

from pymilvus import MilvusClient

from documents.import_manifest import file_hash, get_record, save_record
from documents.markdown_parser import MarkdownParser
from documents.milvus_db import MilvusVectorSave
from utils.env_utils import MILVUS_URI, COLLECTION_NAME

DATA_DIR = Path(r"D:\1pyproject\rag0\md")

def import_one_file(path, parser, client, mv):
    path = Path(path)
    source = str(path)
    digest = file_hash(path)
    record = get_record(source)

    if (
        record
        and record["status"] == "success"
        and record["content_hash"] == digest
    ):
        return {
            "filename": path.name,
            "status": "skipped",
            "chunk_count": record["chunk_count"],
        }

    chunk_count = 0
    try:
        docs = parser.parse_markdown_to_documents(source)
        if not docs:
            raise ValueError("没有解析出正文")

        for doc in docs:
            if len(doc.page_content.encode("utf-8")) > 6000:
                raise ValueError("正文超过 6000 字节")
            for key, value in doc.metadata.items():
                if key != "category_depth":
                    if len(str(value).encode("utf-8")) > 1000:
                        raise ValueError(f"{key} 超过 1000 字节")

        chunk_count = len(docs)
        if file_hash(path) != digest:
            raise RuntimeError("解析期间文件发生变化，请重试")

        save_record(source, digest, chunk_count, "processing")
        expression = f"source == {json.dumps(source, ensure_ascii=False)}"

        client.delete(
            collection_name=COLLECTION_NAME,
            filter=expression,
        )
        mv.add_documents(docs)

        rows = client.query(
            collection_name=COLLECTION_NAME,
            filter=expression,
            output_fields=["count(*)"],
            consistency_level="Strong",
        )
        actual_count = rows[0]["count(*)"]
        if actual_count != chunk_count:
            raise RuntimeError(
                f"块数不一致：预期 {chunk_count}，实际 {actual_count}"
            )

        save_record(source, digest, chunk_count, "success")
        return {
            "filename": path.name,
            "status": "updated",
            "chunk_count": chunk_count,
        }

    except Exception as exc:
        save_record(source, digest, chunk_count, "failed", str(exc))
        raise

def main():
    files = sorted(p for p in DATA_DIR.glob("*.md") if p.is_file())
    if not files:
        raise ValueError("目录中没有 Markdown 文件")

    client = MilvusClient(uri=MILVUS_URI)
    skipped = written = failed = 0

    try:
        if not client.has_collection(collection_name=COLLECTION_NAME):
            raise RuntimeError("集合不存在，请先完成全量入库")

        client.load_collection(collection_name=COLLECTION_NAME)
        parser = MarkdownParser()
        mv = MilvusVectorSave()
        mv.create_connection()

        for path in files:
            try:
                result = import_one_file(path, parser, client, mv)
                if result["status"] == "skipped":
                    skipped += 1
                else:
                    written += 1
                    print(
                        f"已更新：{path.name}，"
                        f"{result['chunk_count']} 块"
                    )
            except Exception as exc:
                failed += 1
                print(f"失败：{path.name}：{exc}")

        print(f"\n未变化跳过：{skipped}")
        print(f"成功更新：{written}")
        print(f"失败：{failed}")

        if failed:
            raise RuntimeError("部分文件导入失败，请处理后重新执行")
    finally:
        client.close()

if __name__ == "__main__":
    main()