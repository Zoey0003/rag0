from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    # add_messages 函数定义了应如何处理状态更新
    # add_messages 表示"追加"（append）
    messages: Annotated[list[BaseMessage], add_messages]
    standalone_question:str


# 数据模型
class Grade(BaseModel):
    """相关性检查的二元评分"""

    binary_score: str = Field(description="相关性评分 'yes' 或 'no'")


    # binary_score: Literal["yes", "no"] = Field(
    #     description="相关性评分"
    # )#更严格的写法

    #后续规定输出格式：
    # structured_llm_grader = llm.with_structured_output(Grade)
    # grade = structured_llm_grader.invoke(...)