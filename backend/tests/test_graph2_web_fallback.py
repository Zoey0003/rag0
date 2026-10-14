from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

# 导入 graph_2 时，自动退出它的交互输入循环。
with patch("builtins.input", return_value="q"):
    import graph2.graph_2 as app

import graph2.retriever_node as retrieve_module
import graph2.grade_documents_node as grade_module
import graph2.generate_node2 as generate_module
import graph2.transform_query_node as transform_module
import graph2.web_search_node as search_module


# 1. 固定从本地知识库开始。
fake_router = Mock()
fake_router.invoke.return_value = SimpleNamespace(
    datasource="vectorstore"
)

# 2. 每次本地检索返回一篇文档。
fake_retriever = Mock()
fake_retriever.invoke.return_value = [
    Document(page_content="这是一篇与测试问题不相关的本地文档。")
]

# 3. 本地文档始终被评为不相关。
fake_document_grader = Mock()
fake_document_grader.invoke.return_value = SimpleNamespace(
    binary_score="no"
)

# 4. 模拟问题改写。
fake_rewrite_llm = RunnableLambda(
    lambda prompt: "改写后的测试问题"
)

# 5. 模拟联网搜索结果。
fake_search = Mock()
fake_search.invoke.return_value = [
    {"content": "这是联网搜索得到的测试资料。",
     "title":"test resource",
     "url":"https://example.com/test",
    }
]

# 6. 模拟答案生成。
fake_generate_llm = RunnableLambda(
    lambda prompt: "这是测试答案。"
)

# 7. 最终答案有资料依据。
fake_grounding_grader = Mock()
fake_grounding_grader.invoke.return_value = SimpleNamespace(
    binary_score="yes"
)

# 8. 最终答案解决了问题。
fake_answer_grader = Mock()
fake_answer_grader.invoke.return_value = SimpleNamespace(
    binary_score="yes"
)


# 临时替换外部调用，保留真实的节点逻辑与图的分支连接。
with (
    patch.object(app, "question_router_chain", fake_router),
    patch.object(app, "hallucination_grader_chain", fake_grounding_grader),
    patch.object(app, "answer_grader_chain", fake_answer_grader),
    patch.object(retrieve_module, "retriever", fake_retriever),
    patch.object(grade_module, "retrieval_grader_chain", fake_document_grader),
    patch.object(transform_module, "llm", fake_rewrite_llm),
    patch.object(search_module, "web_search_tool", fake_search),
    patch.object(generate_module, "llm", fake_generate_llm),
):
    result = app.graph.invoke({
        "original_question": "测试本地无相关资料后转联网",
        "question": "测试本地无相关资料后转联网",
        "transform_count": 0,
        "generation_count": 0,
    })


print("本地检索次数:", fake_retriever.invoke.call_count)
print("文档评分次数:", fake_document_grader.invoke.call_count)
print("改写次数:", result["transform_count"])
print("联网搜索次数:", fake_search.invoke.call_count)
print("生成次数:", result["generation_count"])
print("依据评分次数:", fake_grounding_grader.invoke.call_count)
print("回答有效性评分次数:", fake_answer_grader.invoke.call_count)
print("最终输出:", result["generation"])

assert fake_retriever.invoke.call_count == 3
assert fake_document_grader.invoke.call_count == 3
assert result["transform_count"] == 2
assert fake_search.invoke.call_count == 1
assert result["generation_count"] == 1
assert fake_grounding_grader.invoke.call_count == 1
assert fake_answer_grader.invoke.call_count == 1
assert result["generation"] == "这是测试答案。"

assert isinstance(result["documents"], list)
assert all(isinstance(doc, Document) for doc in result["documents"])
assert len(result["documents"]) == 1
assert (
    result["documents"][0].page_content
    == "这是联网搜索得到的测试资料。"
)
assert result["original_question"] == "测试本地无相关资料后转联网"
assert result["question"] == "改写后的测试问题"

# 确认回答有效性评分使用原始问题。
assert (
    fake_answer_grader.invoke.call_args.args[0]["question"]
    == result["original_question"]
)

doc=result["documents"][0]
assert doc.metadata["source"]=="https://example.com/test"
assert doc.metadata["title"]=="test resource"
assert doc.metadata["source_type"]=="web"

print("本地无相关资料后转联网测试通过")
