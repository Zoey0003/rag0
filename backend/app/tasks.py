from app.core.celery_app import celery_app


@celery_app.task(name="rag0.add")
def add(a: int, b: int) -> int:
    return a + b


@celery_app.task(
        name="rag0.extract_memories",
        autoretry_for=(Exception,),
        retry_backoff=5,
        retry_backoff_max=60,
        retry_jitter=True,
        max_retries=3,
        acks_late=True,#任务执行完成后，才向队列确认。避免刚收到任务就确认，执行中崩溃后任务丢失。
        reject_on_worker_lost=True,#worker 的执行子进程意外退出时，允许任务重新入队。
        )
def extract_memories_task(
    user_id: str,
    source_message_id: int,
) -> None:
    from uuid import UUID

    from app.modules.memory.extractor import extract_and_save_memories

    extract_and_save_memories(
        user_id=UUID(user_id),
        source_message_id=source_message_id,
    )