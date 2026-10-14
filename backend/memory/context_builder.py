from uuid import UUID

import tiktoken
from sqlalchemy.orm import Session

from memory import repository


# 使用通用编码估算长度，不代表 Qwen 的精确 Token 数。
ENCODING = tiktoken.get_encoding("cl100k_base")
HISTORY_TOKEN_BUDGET = 4000 #历史消息预算，不是整个大模型上下文窗口的大小。
PAGE_SIZE = 50


def estimate_message_tokens(role: str, content: str) -> int:
    """估算单条消息的 Token 数，并预留消息格式开销。"""
    return (
        len(ENCODING.encode(role, disallowed_special=()))
        + len(ENCODING.encode(content, disallowed_special=()))
        + 12
    )

#创建最近历史记录 
#返回字典历史记录
def build_recent_history(
    db: Session,#会话
    user_id: UUID,#用户ID
    session_id: UUID,#会话ID
    token_budget: int = HISTORY_TOKEN_BUDGET,#历史 Token 预算
    after_id:int=0,
) -> list[dict[str, str]]:
    """按页回读历史，在预算内保留最近的完整成功问答。"""
    if token_budget <= 0:
        raise ValueError("历史 Token 预算必须大于 0")

    used_tokens = 0 #已使用的 Token 数
    selected_turns = [] #选中的完整问答轮次
    before_id = None #用于分页查询的消息 ID  分页游标
    pending_assistant = None #待处理的ai消息
    finished = False #是否停止读取历史消息


    while not finished:
        rows = repository.list_messages(
            db,
            user_id=user_id,
            session_id=session_id,
            limit=PAGE_SIZE,
            before_id=before_id,#只查指定 ID 之前的消息。
        )
        if not rows:
            break

        # 数据库返回从旧到新，这里反向遍历，优先选最近轮次。
        for item in reversed(rows):
            # 已被摘要覆盖的消息，不再重复放入近期原文。
            if item.id <= after_id:
                finished = True
                break
            if item.status != "success":
                pending_assistant = None
                continue

            if item.role == "assistant":
                pending_assistant = {
                    "id":str(item.id),
                    "role": "assistant",
                    "content": item.content,
                }
                continue

            if item.role != "user" or pending_assistant is None:
                pending_assistant = None
                continue

            user_message = {
                "id":str(item.id),
                "role": "user",
                "content": item.content,
            }
            turn_tokens = (
                estimate_message_tokens("user", item.content)
                + estimate_message_tokens(
                    "assistant",
                    pending_assistant["content"],
                )
            )

            # 放不下就停止，不跳过最近轮次去拼接更早的历史。
            if used_tokens + turn_tokens > token_budget:
                finished = True
                break

            selected_turns.append([
                user_message,
                pending_assistant,
            ])
            used_tokens += turn_tokens
            pending_assistant = None

        # 向更早的消息翻页，跨页的问答也可以配成完整轮次。
        before_id = rows[0].id

        if len(rows) < PAGE_SIZE:
            break

    # 恢复从旧到新的顺序，供模型理解对话。
    history = [
        message
        for turn in reversed(selected_turns)
        for message in turn
    ]
    return history