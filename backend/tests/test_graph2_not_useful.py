from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

# 跳过 graph_2 导入时的交互输入循环。
with patch("builtins.input", return_value="q"):
    import graph2.graph_2 as app

import graph2.retriever_node as retrieve_module
import graph2.grade_documents_node as grade_module
import graph2.generate_node2 as generate_module
import graph2.transform_query_node as transform_module


# 固定走本地检索。
fake_router = Mock()
fake_router.invoke.return_value = SimpleNamespace(
    datasource="vectorstore"
)

# 每次检索都返回一篇测试文档。
fake_retriever = Mock()
fake_retriever.invoke.return_value = [
    Document(page_content="ICP具有高密度、低损伤的特点。")
]

# 文档始终相关。
fake_document_grader = Mock()
fake_document_grader.invoke.return_value = SimpleNamespace(
    binary_score="yes"
)

# 答案始终有资料支持。
fake_grounding_grader = Mock()
fake_grounding_grader.invoke.return_value = SimpleNamespace(
    binary_score="yes"
)

# 但始终没有解决问题，触发改写和重新检索。
fake_answer_grader = Mock()
fake_answer_grader.invoke.return_value = SimpleNamespace(
    binary_score="no"
)

fake_generate_llm = RunnableLambda(lambda prompt: "这是测试答案。")
fake_rewrite_llm = RunnableLambda(lambda prompt: "ICP的表面处理特点是什么？")

with (
    patch.object(app, "question_router_chain", fake_router),
    patch.object(app, "hallucination_grader_chain", fake_grounding_grader),
    patch.object(app, "answer_grader_chain", fake_answer_grader),
    patch.object(retrieve_module, "retriever", fake_retriever),
    patch.object(grade_module, "retrieval_grader_chain", fake_document_grader),
    patch.object(generate_module, "llm", fake_generate_llm),
    patch.object(transform_module, "llm", fake_rewrite_llm),
):
    result = app.graph.invoke({
        "question": "ICP有什么特点？",
        "original_question": "ICP有什么特点？",
        "transform_count": 0,
        "generation_count": 0,
    })

print("生成次数:", result["generation_count"])
print("改写次数:", result["transform_count"])
print("检索次数:", fake_retriever.invoke.call_count)
print("回答有效性评分次数:", fake_answer_grader.invoke.call_count)
print("最终输出:", result["generation"])

assert result["generation_count"] == 3
assert result["transform_count"] == 2
assert fake_retriever.invoke.call_count == 3
assert fake_answer_grader.invoke.call_count == 3
assert "已达到本轮回答的尝试上限" in result["generation"]

print("改写重检路径的次数限制测试通过")
