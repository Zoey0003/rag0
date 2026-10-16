"""登录令牌数据库操作旧导入路径的兼容入口。"""

from app.modules.auth.repository import (
    create_token,
    get_token,
    delete_token,
)

__all__ = ["create_token", "get_token", "delete_token"]