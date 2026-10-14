from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from memory.database import Base


class User(Base):
    """用户表：确定会话和长期记忆的归属。"""

    __tablename__ = "memory_users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatSession(Base):
    """会话表：保存标题、用户归属和时间。"""

    __tablename__ = "memory_sessions"
    __table_args__ = (
        Index("ix_memory_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="新对话"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    # 历史摘要；完整消息仍保留在 memory_messages 表。
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    # 摘要已覆盖到的消息 ID；0 表示尚未生成摘要。
    summary_until_id: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )


class ChatMessage(Base):
    """消息表：持久保存原文、参考资料和执行状态。"""

    __tablename__ = "memory_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_memory_messages_role",
        ),
        CheckConstraint(
            "status IN ('pending', 'success', 'failed')",
            name="ck_memory_messages_status",
        ),
        Index("ix_memory_messages_session_id", "session_id", "id"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )
    sources: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )




class MemoryFact(Base):
    """长期记忆表：保存属于用户、可跨会话使用的记忆。"""

    __tablename__ = "memory_facts"
    __table_args__ = (
        Index("ix_memory_facts_user_created", "user_id", "created_at"),
        CheckConstraint(
            "kind IN ('preference', 'fact')",
            name="ck_memory_facts_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("memory_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # preference：回答偏好；fact：用户背景等信息。
    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="preference",
        server_default="preference",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # 手动录入可以没有来源消息；来自聊天时记录对应消息 ID。
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("memory_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )