from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from memory.models import ChatMessage, ChatSession, User
def create_session(
    db: Session,
    user_id: UUID,
    title: str = "新对话",
) -> ChatSession:
    """为已有用户创建会话，由调用方提交事务。"""
    if db.get(User, user_id) is None:
        raise ValueError("用户不存在")

    title = title.strip()
    if not title or len(title) > 200:
        raise ValueError("会话标题必须为 1～200 个字符")

    chat_session = ChatSession(user_id=user_id, title=title)
    db.add(chat_session)
    db.flush()
    return chat_session


def get_session(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> ChatSession:
    """查询指定用户的会话，检查会话归属。"""
    statement = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    )
    chat_session = db.scalar(statement)

    if chat_session is None:
        raise ValueError("会话不存在或不属于当前用户")

    return chat_session

def delete_session(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> None:
    """删除当前用户的会话，关联消息由数据库级联删除。"""
    chat_session = get_session(db, user_id, session_id)
    db.delete(chat_session)
    db.flush()


def rename_session(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    title: str,
) -> ChatSession:
    """修改指定用户的会话标题，由调用方提交事务。"""
    title = title.strip()
    if not title or len(title) > 200:
        raise ValueError("会话标题必须为 1～200 个字符")

    # 复用现有逻辑，检查会话是否属于该用户。
    chat_session = get_session(db, user_id, session_id)
    chat_session.title = title
    chat_session.updated_at = func.now()
    db.flush()

    return chat_session


def list_sessions(
    db: Session,
    user_id: UUID,
    limit: int = 50,
) -> list[ChatSession]:
    """按最近更新时间查询会话列表，供侧边栏展示。"""
    if not 1 <= limit <= 200:
        raise ValueError("limit 必须在 1～200 之间")

    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(
            ChatSession.updated_at.desc(),
            ChatSession.id.desc(),
        )
        .limit(limit)
    )
    return list(db.scalars(statement))


def set_initial_session_title(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    question: str,
) -> None:
    """首次问答时，用问题生成标题；保留已有自定义标题。"""
    chat_session = get_session(db, user_id, session_id)

    if chat_session.title != "新对话":
        return

    # 已有消息的会话不再自动命名。
    first_message_id = db.scalar(
        select(ChatMessage.id)
        .where(ChatMessage.session_id == session_id)
        .limit(1)
    )
    if first_message_id is not None:
        return

    # 合并换行与空白，最多保留 30 个字符。
    title = " ".join(question.split())
    if not title:
        return

    chat_session.title = (
        title if len(title) <= 30 else title[:29] + "…"
    )
    chat_session.updated_at = func.now()
    db.flush()
