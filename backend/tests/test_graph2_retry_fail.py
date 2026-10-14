from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.runnables import RunnableLambda

# graph_2 导入时会进入输入循环，用 q 自动退出该循环。
with patch("builtins.input", return_value="q"):
    import graph2.graph_2 as app

import graph2.generate_node2 as generate_module
import graph2.web_search_node as search_module

# 原代码写 obj.xxx → mock 时可以用 SimpleNamespace(xxx=...)
# 原代码写 obj["xxx"] → mock 时直接用 ={"xxx": ...}

# 模拟路由：固定进入联网搜索分支。
fake_router = Mock()
fake_router.invoke.return_value = SimpleNamespace(
    datasource="web_search"
)

# 模拟搜索结果。
fake_search = Mock()
fake_search.invoke.return_value = [
    {"content": "这是用于测试重试上限的参考资料。"}
]

# 模拟评分：每次都判定答案没有资料支持。
fake_grader = Mock()
fake_grader.invoke.return_value = SimpleNamespace(
    binary_score="no"
)

# 模拟生成模型，仍然执行原来的 generate 节点和计数逻辑。
fake_llm = RunnableLambda(lambda prompt: "这是测试答案。")

with (
    patch.object(app, "question_router_chain", fake_router),
    patch.object(app, "hallucination_grader_chain", fake_grader),
    patch.object(search_module, "web_search_tool", fake_search),
    patch.object(generate_module, "llm", fake_llm),
):
    result = app.graph.invoke({
        "question": "测试连续评分失败",
        "original_question": "测试连续评分失败",
        "transform_count": 0,
        "generation_count": 0,
    })

print("生成次数:", result["generation_count"])
print("评分次数:", fake_grader.invoke.call_count)
print("最终输出:", result["generation"])

assert result["generation_count"] == 3
assert fake_grader.invoke.call_count == 3
assert "已达到本轮回答的尝试上限" in result["generation"]

print("重试上限测试通过")
