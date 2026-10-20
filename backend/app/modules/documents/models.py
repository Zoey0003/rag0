"""个人文档清单；历史 SQLite 导入记录不自动授予访问权限。"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (UniqueConstraint("owner_id", "filename", name="uq_document_owner_filename"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("memory_users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    active_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
