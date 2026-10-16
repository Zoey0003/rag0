"""用户数据库操作旧导入路径的兼容入口。"""

from app.modules.auth.repository import (
    create_user,
    create_registered_user,
    get_user_by_username,
)

__all__ = [
    "create_user",
    "create_registered_user",
    "get_user_by_username",
]