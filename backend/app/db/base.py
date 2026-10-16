from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全项目共用的 ORM 模型基类。"""