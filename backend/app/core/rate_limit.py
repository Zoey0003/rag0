import hashlib

from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from app.core.redis_client import get_redis, redis_key


# 在 Redis 内一次完成计数和过期设置。
RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


def check_rate_limit(
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    identity_hash = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    key = redis_key(f"rate:{scope}:{identity_hash}")

    try:
        count, ttl = get_redis().eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            window_seconds,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="限流服务暂不可用，请稍后重试",
        ) from None

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后重试",
            headers={"Retry-After": str(max(1, ttl))},
        )


def auth_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"

    check_rate_limit(
        scope="auth",
        identity=ip,
        limit=10,
        window_seconds=60,
    )



TOKEN_BUCKET_SCRIPT = """
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

-- 使用 Redis 时间，让多个 API worker 使用同一时钟。
local time = redis.call('TIME')
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000

local state = redis.call('HMGET', KEYS[1], 'tokens', 'updated_at')
local tokens = tonumber(state[1])
local updated_at = tonumber(state[2])

if tokens == nil or updated_at == nil then
    tokens = capacity
    updated_at = now
end

local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
local retry_after = 0

if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
else
    retry_after = math.ceil((1 - tokens) / refill_rate)
end

redis.call('HSET', KEYS[1],
    'tokens', tostring(tokens),
    'updated_at', tostring(math.max(now, updated_at)))
redis.call('EXPIRE', KEYS[1], ttl)

return {allowed, retry_after}
"""


def check_token_bucket(
    scope: str,
    identity: str,
    capacity: int = 10,
    refill_seconds: int = 6,
) -> None:
    """每 refill_seconds 秒补一个令牌，最多存 capacity 个。"""
    if capacity <= 0 or refill_seconds <= 0:
        raise ValueError("桶容量和补充间隔必须大于 0")

    identity_hash = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    key = redis_key(f"bucket:{scope}:{identity_hash}")

    # 闲置到足以补满之后，才允许删除桶状态。
    ttl = capacity * refill_seconds + 60

    try:
        allowed, retry_after = get_redis().eval(
            TOKEN_BUCKET_SCRIPT,
            1,
            key,
            capacity,
            1 / refill_seconds,
            ttl,
        )
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="限流服务暂不可用，请稍后重试",
        ) from None

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后重试",
            headers={"Retry-After": str(max(1, retry_after))},
        )