import logging
import time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.memory.task_memory import MemoryExtractionTask
from app.modules.memory.task_dispatcher import publish_memory_task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def dispatch_once() -> None:
    # 只读取一批 ID，关闭读取事务后逐条投递。
    with SessionLocal() as db:
        message_ids = list(
            db.scalars(
                select(MemoryExtractionTask.source_message_id)
                .where(
                    MemoryExtractionTask.published_at.is_(None),
                )
                .order_by(
                    MemoryExtractionTask.created_at,
                    MemoryExtractionTask.source_message_id,
                )
                .limit(100)
            )
        )

    for message_id in message_ids:
        try:
            if publish_memory_task(message_id):
                logger.info(
                    "已投递记忆提取任务：来源消息=%s",
                    message_id,
                )
        except Exception:
            logger.exception(
                "待办处理异常：来源消息=%s",
                message_id,
            )


def main() -> None:
    logger.info("记忆提取待办扫描程序已启动")

    try:
        while True:
            try:
                dispatch_once()
            except Exception:
                logger.exception("扫描待办任务失败")

            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("扫描程序已停止")


if __name__ == "__main__":
    main()