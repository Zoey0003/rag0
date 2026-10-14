from collections import Counter
from pathlib import Path

from pymilvus import MilvusClient
from utils.env_utils import MILVUS_URI, COLLECTION_NAME

expected = {p.name for p in Path(r"D:\1pyproject\rag0\md").glob("*.md")}
client = MilvusClient(uri=MILVUS_URI)
iterator = None

try:
    client.load_collection(collection_name=COLLECTION_NAME)
    iterator = client.query_iterator(
        collection_name=COLLECTION_NAME,
        batch_size=500,
        filter="",
        output_fields=["filename", "category"],
        consistency_level="Strong",
    )

    files = Counter()
    categories = Counter()
    total = 0

    while True:
        rows = iterator.next()
        if not rows:
            break
        total += len(rows)
        files.update(row["filename"] for row in rows)
        categories.update(row["category"] for row in rows)

    missing = expected - set(files)
    extra = set(files) - expected

    print("记录数:", total)
    print("文件数:", len(files))
    print("类别:", dict(categories))
    print("缺少文件:", sorted(missing))
    print("额外文件:", sorted(extra))

    assert len(expected) == 430
    assert total == 2177
    assert not missing and not extra
    assert dict(categories) == {"content": 2177}
    print("全量入库核对通过")
finally:
    if iterator is not None:
        iterator.close()
    client.close()