"""旧数据库导入路径的兼容入口。"""

from app.db.base import Base
from app.db.session import (
    ENV_PATH,
    build_database_url,
    check_connection,
    engine,
    SessionLocal,
)

__all__ = [
    "Base",
    "ENV_PATH",
    "build_database_url",
    "check_connection",
    "engine",
    "SessionLocal",
]


if __name__ == "__main__":
    try:
        check_connection()
    finally:
        engine.dispose()