from collections import Counter
from pathlib import Path

from pymilvus import MilvusClient

from documents.import_manifest import connect, file_hash
from utils.env_utils import MILVUS_URI, COLLECTION_NAME

DATA_DIR = Path(r"D:\1pyproject\rag0\md")


def main():
    files = sorted(p for p in DATA_DIR.glob("*.md") if p.is_file())
    assert len(files) == 430, f"文件数不是 430：{len(files)}"

    # 与当前解析器写入的 source 格式一致。
    expected = {str(path): path for path in files}

    client = MilvusClient(uri=MILVUS_URI)
    iterator = None
    counts = Counter()

    try:
        client.load_collection(collection_name=COLLECTION_NAME)
        iterator = client.query_iterator(
            collection_name=COLLECTION_NAME,
            batch_size=500,
            filter="",
            output_fields=["source", "category"],
            consistency_level="Strong",
        )

        while True:
            rows = iterator.next()
            if not rows:
                break
            for row in rows:
                assert row["category"] == "content", "存在非正文记录"
                counts[row["source"]] += 1
    finally:
        if iterator is not None:
            iterator.close()
        client.close()

    missing = set(expected) - set(counts)
    extra = set(counts) - set(expected)

    assert not missing, f"缺少来源：{sorted(missing)}"
    assert not extra, f"额外来源：{sorted(extra)}"
    assert sum(counts.values()) == 2177, "数据库块数不是 2177"

    records = [
        (source, file_hash(path), counts[source], "success", None)
        for source, path in expected.items()
    ]

    conn = connect()
    try:
        with conn:
            existing = conn.execute(
                "SELECT COUNT(*) FROM imports"
            ).fetchone()[0]
            if existing:
                raise RuntimeError("清单已有记录，不重复初始化")

            conn.executemany("""
                INSERT INTO imports
                    (source, content_hash, chunk_count, status, error)
                VALUES (?, ?, ?, ?, ?)
            """, records)
    finally:
        conn.close()

    print("基线文件数:", len(records))
    print("数据库文档块数:", sum(counts.values()))
    print("导入基线建立完成")


if __name__ == "__main__":
    main()