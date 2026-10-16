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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



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
