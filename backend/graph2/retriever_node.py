from uuid import UUID

from app.db.session import SessionLocal
from app.modules.documents.repository import retrieval_expression
from utils.log_utils import log


def retrieve(state):
    """
    检索相关文档
    Args:
        state (dict): 当前图状态，包含用户问题

    Returns:
        state (dict): 更新后的状态，新增包含检索结果的documents字段
    """
    log.info("---去知识库中检索文档---")  # 打印当前阶段标识
    question = state["question"]  # 从状态中获取用户问题
    # 文档检索
    # 缺少认证身份时禁止回退到共享语料。
    owner_id = state.get("user_id")
    if not owner_id:
        return {"documents": [], "question": question}
    with SessionLocal() as db:
        expression = retrieval_expression(db, UUID(owner_id))
    if expression is None:
        return {"documents": [], "question": question}
    from tools.retriever_tools import mv

    # 每次请求独立传递过滤条件，不修改全局检索器。
    documents = mv.vector_store_saved.similarity_search(
        question, k=4, expr=expression,
        ranker_type="rrf", ranker_params={"k": 100},
    )
    return {"documents": documents, "question": question}  # 返回更新后的状态
