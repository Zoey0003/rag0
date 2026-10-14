from collections import Counter
from pathlib import Path

from pymilvus import MilvusClient
from utils.env_utils import MILVUS_URI, COLLECTION_NAME


# directory = Path(__file__).parent / "datas" / "batch_test_20_md"

directory = (
    Path(__file__).resolve().parents[1]
    / "datas"
    / "batch_test_20_md"
)
expected_files = {
    path.name
    for path in directory.glob("*.md")
    if path.is_file()
}

assert len(expected_files) == 20, "测试目录中的文件数不是20"

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

    missing_files = expected_files - set(file_counts)
    extra_files = set(file_counts) - expected_files

    print("集合名称:", COLLECTION_NAME)
    print("查询到的记录数:", len(rows))
    print("数据库中的文件数:", len(file_counts))

    print("\n各文件的文档块数:")
    for filename, count in sorted(file_counts.items()):
        print(f"{filename}: {count}")

    print("\n类别统计:", dict(category_counts))
    print("缺少的文件:", sorted(missing_files))
    print("多出的文件:", sorted(extra_files))

    assert len(rows) == 102, "记录总数与入库日志不一致"
    assert not missing_files, "有文件没有出现在数据库中"
    assert not extra_files, "数据库中存在本次目录之外的文件"
    assert dict(category_counts) == {"content": 102}, "类别不符合预期"

    print("\n20文件入库核对通过")

finally:
    client.close()