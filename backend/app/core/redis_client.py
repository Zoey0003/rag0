# Redis 连接与键前缀

import os
from functools import lru_cache

from dotenv import load_dotenv
from redis import Redis

from utils.env_utils import ENV_PATH


# 使用项目已有的 backend/.env 路径。
load_dotenv(ENV_PATH, override=False)


def redis_key(name: str) -> str:
    """为 Redis 键添加项目专属前缀。"""
    prefix = os.getenv("REDIS_PREFIX", "rag0")
    return f"{prefix}:{name}"


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """每个进程复用一个客户端及其连接池。"""
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )