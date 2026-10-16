"""密码工具旧导入路径的兼容入口。"""

from app.modules.auth.password import (
    hash_password,
    verify_password,
)

__all__ = ["hash_password", "verify_password"]