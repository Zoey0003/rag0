import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import  sessionmaker
from app.db.base import Base

# 固定读取源码目录的 .env，不依赖终端当前目录。
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=False)





def build_database_url():
    """读取数据库参数，正确处理密码中的特殊字符。"""
    password = os.getenv("MEMORY_DB_PASSWORD")
    if not password:
        raise RuntimeError("未配置 MEMORY_DB_PASSWORD")

    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("MEMORY_DB_USER", "rag_user"),
        password=password,
        host=os.getenv("MEMORY_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("MEMORY_DB_PORT", "5432")),
        database=os.getenv("MEMORY_DB_NAME", "rag_memory"),
    )


engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


def check_connection():
    """只读检查数据库连接，不创建或修改业务表。"""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
        print("数据库连接成功:", result)


if __name__ == "__main__":
    try:
        check_connection()
    finally:
        engine.dispose()