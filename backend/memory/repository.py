"""数据库操作兼容入口，保留原有 repository.<函数名> 调用方式。

具体实现位于 repositories；新模块不要反向导入本文件。
"""

from memory.repositories.user import create_user
from memory.repositories.sessions import (
    create_session,
    delete_session,
    get_session,
    list_sessions,
    rename_session,
    set_initial_session_title,
)
from memory.repositories.messages import list_all_messages, list_messages, save_message
from memory.repositories.summaries import (
    get_session_summary,
    list_messages_for_summary,
    save_session_summary,
)
from memory.repositories.memories import (
    delete_memory,
    list_memories,
    save_memory,
)

__all__ = [
    "create_user",
    "create_session",
    "delete_session",
    "get_session",
    "list_sessions",
    "rename_session",
    "set_initial_session_title",
    "list_messages",
    "list_all_messages",
    "save_message",
    "get_session_summary",
    "list_messages_for_summary",
    "save_session_summary",
    "delete_memory",
    "list_memories",
    "save_memory",
]
