from pathlib import Path
from collections import Counter

from documents.markdown_parser import MarkdownParser


parser = MarkdownParser()
# directory = Path(__file__).parent / "datas" / "batch_test_md"
directory = (
    Path(__file__).resolve().parents[1]
    / "datas"
    / "batch_test_md"
)
for path in sorted(directory.glob("*.md")):
    docs = parser.parse_markdown_to_documents(str(path))

    print("\n文件:", path.name)
    print("文档块数:", len(docs))
    print("类别统计:", dict(Counter(
        doc.metadata["category"] for doc in docs
    )))

    for index, doc in enumerate(docs, start=1):
        print(f"\n块 {index}")
        print("标题:", doc.metadata["title"])
        print("内容预览:", doc.page_content[:180])

    assert docs, f"{path.name} 没有解析出正文"
    assert all(doc.metadata["category"] == "content" for doc in docs)

print("\nMarkdown标题分块验证完成")