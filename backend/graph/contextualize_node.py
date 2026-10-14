from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from llm_models.all_llm import llm
from utils.log_utils import log


def contextualize(state):
    messages = state["messages"]

    # 找到当前轮用户问题所在的位置
    current_index = next(
        i
        for i in range(len(messages) - 1, -1, -1)
        if isinstance(messages[i], HumanMessage)
    )
    question = messages[current_index].content

    # 只保留之前的用户问题和普通回答，排除工具调用及工具结果
    history = [
        message
        for message in messages[:current_index]
        if isinstance(message, HumanMessage)
        or (
            isinstance(message, AIMessage)
            and not message.tool_calls
        )
    ]

    if not history:
        standalone_question = question
    else:
        prompt = ChatPromptTemplate.from_messages([
            (
                # "system",
                # "根据历史对话，将当前问题补全成无需历史也能理解的独立问题。"
                # "只解决代词、省略和指代，不回答问题，不扩展用户需求。"
                # "必须保留用户的限制，例如只查本地知识库、资料不足就说明。"
                # "如果问题已经完整，原样输出；如果指代无法确定，不要猜测。"
                # "历史回答只用于理解指代，不作为事实依据。"
                # "只输出补全后的问题，不输出理由或说明。"
                "system",
                "你只负责将当前问题中的代词或省略内容，替换为历史对话中明确的指代对象。"
                "只做最小必要修改，保留原问题的范围、语气和所有限制。"
                "禁止新增比较维度、子问题、应用场景或回答要求。"
                "不要因为历史回答包含某个细节，就把它加入当前问题。"
                "当前问题已经独立完整时，原样输出；指代无法确定时，不要猜测。"
                "不回答问题，不输出理由、标题或解释，只输出补全后的问题。"
                "/n示例："
                "/n历史问题：什么是电感耦合等离子体（ICP）？"
                "/n当前问题：它和电容耦合等离子体相比有什么区别？"
                "/n输出：电感耦合等离子体（ICP）和电容耦合等离子体相比有什么区别？"


            ),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ])

        chain = prompt | llm | StrOutputParser()
        standalone_question = chain.invoke({
            "history": history,
            "question": question,
        }).strip()

        if not standalone_question:
            standalone_question = question

    log.info(f"当前轮独立问题: {standalone_question}")
    return {"standalone_question": standalone_question}