from collections import Counter

from pymilvus import MilvusClient
from utils.env_utils import MILVUS_URI, COLLECTION_NAME


client = MilvusClient(uri=MILVUS_URI)

try:
    client.load_collection(collection_name=COLLECTION_NAME)

    rows = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["filename", "category"],
        limit=1000,
        consistency_level="Strong",
    )

    file_counts = Counter(row["filename"] for row in rows)
    category_counts = Counter(row["category"] for row in rows)

    print("集合名称:", COLLECTION_NAME)
    print("查询到的记录数:", len(rows))

    print("\n各文件的文档块数:")
    for filename, count in sorted(file_counts.items()):
        print(f"{filename}: {count}")

    print("\n各类别的文档块数:")
    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

    # assert len(rows) == 18, "记录数与入库日志不一致"
    # assert set(file_counts) == {
    #     "tech_report_0lf3t9s7.md",
    #     "tech_report_0ls2kg7u.md",
    # }, "数据库中的文件与本次测试文件不一致"
    # assert sorted(file_counts.values()) == [4, 14], "各文件块数不符合预期"

    assert len(rows) == 7, "记录总数应为7"

    assert dict(file_counts) == {
        "tech_report_0lf3t9s7.md": 6,
        "tech_report_0ls2kg7u.md": 1,
    }, "各文件的文档块数不符合预期"

    assert dict(category_counts) == {
        "content": 7,
    }, "所有文档块都应为content"

    print("\n新解析方式入库核对通过")

    print("\n两文件入库数据核对通过")

finally:
    client.close()