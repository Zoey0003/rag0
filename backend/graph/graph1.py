import uuid
from typing import Literal, List

from graph.contextualize_node import contextualize

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from draw_png import draw_graph
from graph.agent_node import agent_node
from graph.generate_node import generate
from graph.get_human_message import get_last_human_message
from graph.graph_state1 import AgentState, Grade
from graph.rewrite_node import rewrite
from llm_models.all_llm import llm
from tools.retriever_tools import retriever_tool
from utils.log_utils import log
from utils.print_utils import _print_event




def grade_documents(state) -> Literal["generate", "insufficient"]:
    """
    判断检索到的文档是否与问题相关。
    参数:
        state (messages): 当前状态
    返回:
        str: 判断结果，文档是否相关
    """
    log.info("---检查document的相关性---")
    #  带结构化输出的LLM
    llm_with_structured = llm.with_structured_output(
        Grade,
        method="function_calling",)

    # 提示模板
    prompt = PromptTemplate(
        template="""你是一个评估检索文档与用户问题相关性的评分器。\n
            这是检索到的文档：\n\n {context} \n\n
            这是用户的问题：{question} \n
            如果文档包含与用户问题相关的关键词或语义含义，则评为相关。\n
            给出二元评分 'yes' 或 'no' 来表示文档是否与问题相关。""",
        input_variables=["context", "question"],
    )#此时context是检索到的文档，question是用户问题

    # 处理链
    #调用llm给context和question打分，输出Grade模型
    chain = prompt | llm_with_structured

    messages = state["messages"]#消息列表
    last_message = messages[-1]#文档消息

    question = get_last_human_message(messages).content
    docs = last_message.content

    scored_result = chain.invoke({"question": question, "context": docs})

    score = scored_result.binary_score

    if score == "yes":
        print("---输出：文档相关---")
        return "generate"

    else:
        print("---输出：文档不相关---")
        return "insufficient"


def insufficient(state):
    return {
        "messages": [
            AIMessage(
                content="本地知识库中未找到与问题相关的资料，资料不足，无法根据知识库回答。"
            )
        ]
    }


# 定义一个新的工作流图
#状态图
workflow = StateGraph(AgentState)

# 添加节点
#函数注册进图
#节点和函数对应
workflow.add_node('contextualize',contextualize)
workflow.add_node('agent', agent_node)
workflow.add_node('retrieve', ToolNode([retriever_tool]))
workflow.add_node('rewrite', rewrite)
workflow.add_node('generate', generate)
workflow.add_node("insufficient", insufficient)
workflow.add_edge(START, 'contextualize')#程序从agent节点开始
workflow.add_edge("contextualize","agent")
workflow.add_conditional_edges(#agent的下一个节点是tool判断
    'agent',
    tools_condition,
    {
        'tools': 'retrieve',
        END: END
    }
)

workflow.add_conditional_edges(
    'retrieve',
    grade_documents,
)

workflow.add_edge('insufficient', END)
workflow.add_edge('rewrite', 'agent')
workflow.add_edge('generate', END)


# 检查点让状态图可以持久化其状态
# 这是整个状态图的完整内存
memory = MemorySaver()

# 编译状态图，配置检查点为memory, 配置中断点
#编译这个图，同时给它开启 checkpoint
graph = workflow.compile(checkpointer=memory)#同一个会话state和message可以保存


# draw_graph(graph, 'graph_rag1-2.png')
config = {
    "configurable": {
        # 检查点由session_id访问
        "thread_id": str(uuid.uuid4()),
    },
    "recursion_limit":8,#工作流步数上限
    #限制 LangGraph 一次运行最多走多少个 step
}

_printed = set()  # set集合，避免重复打印

# 执行工作流
while True:
    question = input('用户：')
    if question.lower() in ['q', 'exit', 'quit']:
        log.info('对话结束，拜拜！')
        break
    else:
        inputs = {
            "messages": [
                ("user", question),
            ]
        }
        events = graph.stream(inputs, config=config, stream_mode='values')
        # 打印消息
        for event in events:
            _print_event(event, _printed)