from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from memory.models import AuthToken


def create_token(
    db: Session,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> None:
    """保存令牌哈希，由调用方提交事务。"""
    token = AuthToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token)
    db.flush()

def get_token(
    db: Session,
    token_hash: str,
) -> AuthToken | None:
    """按哈希查询登录令牌。"""
    return db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash
        )
    )


def delete_token(
    db: Session,
    token_hash: str,
) -> None:
    """删除当前登录令牌，由调用方提交事务。"""
    token = get_token(db, token_hash)

    if token is not None:
        db.delete(token)
        db.flush()