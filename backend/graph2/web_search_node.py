from langchain_core.documents import Document

from llm_models.all_llm import web_search_tool
from utils.log_utils import log


# def web_search(state):
#     """
#     基于优化后的问题进行网络搜索

#     Args:
#         state (dict): 当前图状态，包含优化后的问题

#     Returns:
#         state (dict): 更新后的状态，documents字段替换为网络搜索结果
#     """
#     log.info("---WEB SEARCH---")  # 阶段标识
#     question = state["question"]  # 获取优化后的问题

#     # 执行网络搜索
#     docs = web_search_tool.invoke({"query": question})  # 调用网络搜索工具
#     web_results = "\n".join([d["content"] for d in docs])  # 合并搜索结果
#     web_results = Document(page_content=web_results)  # 转换为文档格式

#     return {"documents": [web_results], "question": question}  # 返回更新状态


def web_search(state):
    """联网搜索，将每条结果保存为带来源信息的文档。"""
    log.info("---WEB SEARCH---")
    question = state["question"]

    results = web_search_tool.invoke({"query": question})

    documents = [
        Document(
            page_content=item["content"],
            metadata={
                "source": item.get("url", ""),
                "title": item.get("title", ""),
                "source_type": "web",
            },
        )
        for item in results
    ]
    return {"documents": documents}