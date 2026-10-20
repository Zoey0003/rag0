"""加载全部 ORM 模型，供 Alembic 获取完整表结构。"""
#汇总模型
from app.modules.auth.models import AuthToken, User
from app.modules.conversations.models import (
    ChatMessage,
    ChatSession,
)
from memory.models import MemoryFact
from app.modules.memory.task_memory import MemoryExtractionTask
from app.modules.documents.models import KnowledgeDocument
__all__ = [
    "User",
    "AuthToken",
    "ChatSession",
    "ChatMessage",
    "MemoryFact",
    "MemoryExtractionTask",
    "KnowledgeDocument",
]
