"""消息数据库操作旧路径的兼容入口。"""

from app.modules.conversations.repository import (
    save_message,
    list_all_messages,
    list_messages,
)

__all__ = [
    "save_message",
    "list_all_messages",
    "list_messages",
]