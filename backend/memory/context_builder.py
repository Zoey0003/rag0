from uuid import UUID

import tiktoken
from sqlalchemy.orm import Session

from memory import repository
"""近期上下文构建器旧路径的兼容入口。"""

from app.modules.memory.context_builder import build_recent_history

__all__ = ["build_recent_history"]

# 使用通用编码估算长度，不代表 Qwen 的精确 Token 数。
ENCODING = tiktoken.get_encoding("cl100k_base")
HISTORY_TOKEN_BUDGET = 4000 #历史消息预算，不是整个大模型上下文窗口的大小。
PAGE_SIZE = 50


def estimate_message_tokens(role: str, content: str) -> int:
    """估算单条消息的 Token 数，并预留消息格式开销。"""
    return (
        len(ENCODING.encode(role, disallowed_special=()))
        + len(ENCODING.encode(content, disallowed_special=()))
        + 12
    )
