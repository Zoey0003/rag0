import logging
from contextlib import contextmanager
from threading import Event, Thread

from redis.exceptions import LockError, RedisError

from app.core.redis_client import get_redis, redis_key


logger = logging.getLogger(__name__)


class ResourceBusyError(Exception):
    """资源正在被其他请求处理。"""


class ResourceLockLostError(Exception):
    """锁已丢失，不能继续关键写入。"""


class LockGuard:
    def __init__(self, lock, lost):
        self.lock = lock
        self.lost = lost

    def ensure_owned(self):
        """在关键写入前检查锁是否仍属于当前请求。"""
        if self.lost.is_set() or not self.lock.owned():
            raise ResourceLockLostError("资源锁已丢失")


@contextmanager
def resource_lock(resource: str, lease_seconds: int = 30):
    if lease_seconds < 10:
        raise ValueError("锁的有效期至少为 10 秒")

    lock = get_redis().lock(
        name=redis_key(f"lock:{resource}"),
        timeout=lease_seconds,
        # 续期线程需要访问获取锁线程保存的持有者标识。
        thread_local=False,
    )

    if not lock.acquire(blocking=False):
        raise ResourceBusyError(f"资源正在处理中：{resource}")

    stop = Event()
    lost = Event()
    guard = LockGuard(lock, lost)

    def renew():
        while not stop.wait(lease_seconds / 3):
            try:
                lock.extend(
                    lease_seconds,
                    replace_ttl=True,
                )
            except (RedisError, LockError):
                lost.set()
                logger.exception("资源锁续期失败：%s", resource)
                return

    thread = Thread(target=renew, daemon=True)

    try:
        thread.start()
        yield guard
        guard.ensure_owned()
    finally:
        stop.set()

        if thread.is_alive():
            thread.join()

        try:
            lock.release()
        except (RedisError, LockError):
            logger.exception("资源锁释放失败：%s", resource)