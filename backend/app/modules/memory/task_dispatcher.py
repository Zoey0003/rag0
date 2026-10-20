import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.conversations.models import ChatMessage, ChatSession
from app.modules.memory.task_memory import MemoryExtractionTask
from app.tasks import extract_memories_task


logger = logging.getLogger(__name__)


def publish_memory_task(source_message_id: int) -> bool:
    with SessionLocal.begin() as db:
        # 多个投递程序并发时，同一条待办只由一个程序处理。
        task = db.scalar(
            select(MemoryExtractionTask)
            .where(
                MemoryExtractionTask.source_message_id
                == source_message_id,
                MemoryExtractionTask.published_at.is_(None),
            )
            .with_for_update(skip_locked=True)
        )

        if task is None:
            return False

        user_id = db.scalar(
            select(ChatSession.user_id)
            .join(
                ChatMessage,
                ChatMessage.session_id == ChatSession.id,
            )
            .where(ChatMessage.id == source_message_id)
        )

        if user_id is None:
            task.last_error = "来源消息或会话不存在"
            return False

        try:
            extract_memories_task.apply_async(
                kwargs={
                    "user_id": str(user_id),
                    "source_message_id": source_message_id,
                },
                retry=False,
            )
        except Exception as exc:
            # 不填写 published_at，保留给后续再次投递。
            task.last_error = type(exc).__name__
            logger.exception(
                "记忆提取任务投递失败：来源消息=%s",
                source_message_id,
            )
            return False

        task.published_at = datetime.now(timezone.utc)
        task.last_error = None

    return True