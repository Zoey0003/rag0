"""认证依赖旧导入路径的兼容入口。"""

from app.modules.auth.dependencies import (
    bearer,
    require_user_id,
)

__all__ = ["bearer", "require_user_id"]