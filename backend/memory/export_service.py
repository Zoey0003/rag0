"""会话导出服务旧路径的兼容入口。"""

from app.modules.conversations.export_service import (
    export_session_markdown,
)

__all__ = ["export_session_markdown"]