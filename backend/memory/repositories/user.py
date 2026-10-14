from sqlalchemy.orm import Session
from memory.models import User

def create_user(db: Session, name: str) -> User:
    """创建用户，由调用方提交事务。"""
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("用户名必须为 1～100 个字符")

    user = User(name=name)
    db.add(user)
    db.flush()
    return user
