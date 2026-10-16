from sqlalchemy.orm import Session
from memory.models import User
from sqlalchemy import select
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