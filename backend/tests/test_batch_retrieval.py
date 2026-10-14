from tools.retriever_tools import retriever


questions = [
    "晶圆级封装为什么能降低成本？",
    "高深宽比等离子体刻蚀需要控制哪些因素？",
]

for question in questions:
    print("\n" + "=" * 60)
    print("问题:", question)

    docs = retriever.invoke(question)
    print("返回文档数:", len(docs))

    for index, doc in enumerate(docs, start=1):
        print(f"\n结果 {index}")
        print("文件:", doc.metadata.get("filename"))
        print("类别:", doc.metadata.get("category"))
        print("标题:", doc.metadata.get("title"))
        print("正文:", doc.page_content)

    assert docs, "没有检索到任何文档"
    assert all(
        doc.metadata.get("category") == "content"
        for doc in docs
    ), "检索结果中出现了非content文档"

print("\n检索调用完成，请检查内容相关性")