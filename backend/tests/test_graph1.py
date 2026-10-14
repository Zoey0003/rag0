from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from llm_models.all_llm import llm


@tool
def search_knowledge(query: str) -> str:
    """根据问题搜索本地知识库。"""
    return "测试工具，不实际检索。"


question = "请搜索等离子体表面处理的原理。"
print("实际输入:", question)
print("输入编码:", ascii(question))

tool_model = llm.bind_tools(
    [search_knowledge],
    tool_choice="search_knowledge",
)
response = tool_model.invoke(question)

print("工具调用:", response.tool_calls)


class RelevanceGrade(BaseModel):
    """文档相关性评分。"""

    relevant: Literal["yes", "no"] = Field(
        description="文档与问题相关时为 yes，否则为 no"
    )


grader = llm.with_structured_output(
    RelevanceGrade,
    method="function_calling",
)
grade = grader.invoke(
    "判断文档是否与问题相关。"
    "问题：等离子体如何改善材料表面？"
    "文档：等离子体通过离子轰击和自由基反应改变材料表面性质。"
)
print("结构化评分:", grade.model_dump())