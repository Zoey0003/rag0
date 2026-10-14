from graph2.query_route_chain import question_router_chain

questions = [
    "等离子体通过哪些机制改善半导体材料的表面性质？",
    "RAG是什么？",
]

for question in questions:
    result = question_router_chain.invoke({"question": question})
    print("问题:", question)
    print("选择的数据源:", result.datasource)
    print("-" * 40)