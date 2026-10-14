from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm_models.all_llm import llm


# 数据模型 - 文档相关性评分
class GradeDocuments(BaseModel):
    """对检索到的文档进行相关性评分的二元判断"""

    binary_score: str = Field(
        description="文档是否与问题相关，取值为'yes'或'no'"
    )


# 带函数调用的LLM初始化
structured_llm_grader = llm.with_structured_output(
    GradeDocuments,
    method="function_calling",
)  # 绑定结构化输出到评分模型

# 提示词模板
system = """你是检索文档相关性评分器。
只有文档能够直接帮助回答用户问题时，才返回 yes。
不能仅因为关键词相同或主题相近就判为相关。

对于工艺问题，应核对文档讨论的工艺、对象和目的是否匹配。
例如：高深宽比刻蚀问题，不能仅因文档提到等离子体，
就接受表面清洗、表面改性或沉积工艺的参数。

直接支持回答返回 yes，否则返回 no。
"""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色提示
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),  # 用户输入模板
    ]
)

# 构建检索评分器工作流
retrieval_grader_chain = grade_prompt | structured_llm_grader  # 组合提示模板和LLM评分器
