from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.conversations.models import ChatMessage, ChatSession
from app.modules.conversations.repository import get_session
from app.modules.memory.models import MemoryFact

def save_memory(
    db: Session,
    user_id: UUID,
    content: str,
    kind: str = "preference",
    source_message_id: int | None = None,
) -> MemoryFact:
    """保存长期记忆，校验来源归属，并复用完全相同的记忆。"""
    content = content.strip()

    if not content or len(content) > 1000:
        raise ValueError("记忆内容必须为 1～1000 个字符")

    if kind not in {"preference", "fact"}:
        raise ValueError("记忆类型必须为 preference 或 fact")

    if db.get(User, user_id) is None:
        raise ValueError("用户不存在")

    if source_message_id is not None:
        # 来源消息必须属于该用户，不能引用其他用户的消息。
        source = db.scalar(
            select(ChatMessage)
            .join(
                ChatSession,
                ChatMessage.session_id == ChatSession.id,
            )
            .where(
                ChatMessage.id == source_message_id,
                ChatSession.user_id == user_id,
            )
        )
        if source is None:
            raise ValueError("来源消息不存在或不属于当前用户")

    existing = db.scalar(
        select(MemoryFact)
        .where(
            MemoryFact.user_id == user_id,
            MemoryFact.kind == kind,
            MemoryFact.content == content,
        )
        .order_by(MemoryFact.created_at.asc(), MemoryFact.id.asc())
        .limit(1)
    )
    if existing is not None:
        return existing

    memory = MemoryFact(
        user_id=user_id,
        kind=kind,
        content=content,
        source_message_id=source_message_id,
    )
    db.add(memory)
    db.flush()
    return memory


def list_memories(
    db: Session,
    user_id: UUID,
    limit: int = 50,
) -> list[MemoryFact]:
    """按创建时间倒序读取用户的长期记忆。"""
    if not 1 <= limit <= 200:
        raise ValueError("limit 必须在 1～200 之间")

    if db.get(User, user_id) is None:
        raise ValueError("用户不存在")

    statement = (
        select(MemoryFact)
        .where(MemoryFact.user_id == user_id)
        .order_by(
            MemoryFact.created_at.desc(),
            MemoryFact.id.desc(),
        )
        .limit(limit)
    )
    return list(db.scalars(statement))


def delete_memory(
    db: Session,
    user_id: UUID,
    memory_id: UUID,
) -> None:
    """删除指定用户的一条长期记忆，由调用方提交事务。"""
    memory = db.scalar(
        select(MemoryFact).where(
            MemoryFact.id == memory_id,
            MemoryFact.user_id == user_id,
        )
    )
    if memory is None:
        raise ValueError("记忆不存在或不属于当前用户")

    db.delete(memory)
    db.flush()

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

    if expected_until_id < 0 or new_until_id <= expected_until_id:        raise ValueError("新的摘要进度必须大于原进度")

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