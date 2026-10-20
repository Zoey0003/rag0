from typing import TypedDict, List

from langchain_core.documents import Document


class GraphState(TypedDict):
    """
    表示图处理流程的状态信息

    属性说明：
        question: 用户提出的问题文本
        generation: 语言模型生成的回答文本
        transform_count: 传换查询的次数
        documents: 检索到的相关文档列表
    """

    question: str  # 当前检索问题 后续可能会被改写
    transform_count: int  # 传换查询的次数
    generation: str  # 存储LLM生成的回答内容
    documents: List[Document]  # 存储检索到的文档内容列表
    generation_count: int  # 当前问题累计生成答案的次数
    original_question:str
    user_preferences: str  # 当前用户的长期回答偏好
    user_id: str  # 由认证后的 API 注入
