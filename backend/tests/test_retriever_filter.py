from tools.retriever_tools import retriever

question = "等离子体改善半导体材料表面性质的机制"
docs = retriever.invoke(question)

print("返回文档数:", len(docs))

for i, doc in enumerate(docs, start=1):
    print(f"\n结果 {i}")
    print("类别:", doc.metadata.get("category"))
    print("标题:", doc.metadata.get("title"))
    print("内容预览:", doc.page_content[:100])

unexpected = [
    doc for doc in docs
    if doc.metadata.get("category") != "content"
]

print("\n非 content 文档数:", len(unexpected))