from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.models import ChatMessage, ChatSession
from memory.repositories.sessions import get_session


def get_session_summary(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> tuple[str, int]:
    """读取会话摘要及其覆盖到的消息 ID。"""
    chat_session = get_session(db, user_id, session_id)
    return (
        chat_session.summary,
        chat_session.summary_until_id,
    )


def list_messages_for_summary(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    after_id: int,
    through_id: int,
    limit: int = 100,
) -> list[ChatMessage]:
    """按时间顺序读取指定区间内尚未压缩的成功消息。"""
    if not 1 <= limit <= 500:
        raise ValueError("limit 必须在 1～500 之间")

    if after_id < 0 or through_id < after_id:
        raise ValueError("摘要消息区间不合法")

    get_session(db, user_id, session_id)

    statement = (
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.status == "success",
            ChatMessage.id > after_id,
            ChatMessage.id <= through_id,
        )
        .order_by(ChatMessage.id.asc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def save_session_summary(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    summary: str,
    expected_until_id: int,
    new_until_id: int,
) -> None:
    """锁定会话，检查摘要进度，再原子更新摘要和覆盖位置。"""
    if not summary.strip():
        raise ValueError("摘要不能为空")

    if expected_until_id < 0 or new_until_id <= expected_until_id:
        raise ValueError("新的摘要进度必须大于原进度")

    statement = (
        select(ChatSession)
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    chat_session = db.scalar(statement)

    if chat_session is None:
        raise ValueError("会话不存在或不属于当前用户")

    # 防止较早生成的摘要覆盖其他请求已经更新的摘要。
    if chat_session.summary_until_id != expected_until_id:
        raise ValueError("摘要进度已改变，需要重新读取")

    # 摘要应当覆盖到一个完整问答的助手消息。
    last_message = db.scalar(
        select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.id == new_until_id,
            ChatMessage.role == "assistant",
            ChatMessage.status == "success",
        )
    )
    if last_message is None:
        raise ValueError("摘要结束位置必须是本会话的成功助手消息")

    chat_session.summary = summary.strip()
    chat_session.summary_until_id = new_until_id
    db.flush()
