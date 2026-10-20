from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryExtractionTask(Base):
    """记录需要投递的记忆提取任务。"""

    __tablename__ = "memory_extraction_tasks"

    # 一条来源消息只需要一条待办记录。
    source_message_id: Mapped[int] = mapped_column(
        ForeignKey("memory_messages.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # NULL 表示尚未成功投递；不代表提取是否完成。
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )