from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.modules.auth.models import AuthToken,User


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


def create_user(db: Session, name: str) -> User:
    """创建用户，由调用方提交事务。"""
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("用户名必须为 1～100 个字符")

    user = User(name=name)
    db.add(user)
    db.flush()
    return user

#创建用户
def create_registered_user(
    db: Session,
    username: str,
    name: str,
    password_hash: str,
) -> User:
    """创建有账号密码的用户，由调用方提交事务。"""
    user = User(
        username=username,
        name=name,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()

    return user


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    """按登录账号查找用户，不存在时返回 None。"""
    statement = select(User).where(
        User.username == username
    )
    return db.scalar(statement)