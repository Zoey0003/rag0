#sqlalchemy的表列键约束等
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class User(Base):
    """用户表：确定会话和长期记忆的归属。"""

    __tablename__ = "memory_users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    name:Mapped[str]=mapped_column(String(100),nullable=False)
    username:Mapped[str|None]=mapped_column(
        String(64),
        unique=True,
        nullable=True,)
    password_hash:Mapped[str|None]=mapped_column(
        String(256),
        nullable=False,
    )
class AuthToken(Base):
    __tablename__="auth_tokens"
    token_hash:Mapped[str]=mapped_column(
        String(64),
        primary_key=True,
    )
    user_id:Mapped[UUID]=mapped_column(
        ForeignKey("memory_users.id"),#forrign列=主表的某列 设置外键的这个是从表
        nullable=False,
        index=True,#默认创建b+ index

    )
    expires_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        nullable=False
    )# 过期时间