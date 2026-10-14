from unittest.mock import patch

with patch("builtins.input", return_value="q"):
    import graph2.graph_2 as app

questions = [
    "WLP相比传统封装，成本优势来自哪些方面？成本降幅有什么适用条件？",
    "加工高深宽比结构时，刻蚀时间、能量密度和掩膜分别有什么作用？",
]

for q in questions:
    print("\n" + "=" * 80)
    print("QUESTION:", q)

    result = app.graph.invoke({
        "question": q,
        "original_question": q,
        "transform_count": 0,
        "generation_count": 0,
    })

    generation = result.get("generation", "")
    docs = result.get("documents", [])

    print("FINAL ANSWER:")
    print(generation)

    print("DOC_COUNT:", len(docs))
    for i, d in enumerate(docs[:3], 1):
        print(f"\n-- doc {i}")
        print("filename:", d.metadata.get("filename"))
        print("category:", d.metadata.get("category"))
        print("title:", d.metadata.get("title"))
        print("content:", d.page_content[:300].replace("\n", " "))

    assert docs, "未检索到相关文档"
    assert all(doc.metadata.get("category") == "content" for doc in docs), \
        "检索结果里混入了非 content 类别"

print("\ngraph2 20-file validation finished.")