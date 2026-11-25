"""Redis backed sliding window rate limiter."""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


def check_rate_limit(key: str) -> None:
    now = time.time()
    member = f"{now:.6f}:{uuid.uuid4().hex}"
    redis_key = "rate:" + hashlib.sha256(key.encode()).hexdigest()
    script = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
    local count = redis.call('ZCARD', KEYS[1])
    if count >= tonumber(ARGV[2]) then return count end
    redis.call('ZADD', KEYS[1], ARGV[3], ARGV[4])
    redis.call('EXPIRE', KEYS[1], 61)
    return count
    """
    count = int(r.eval(script, 1, redis_key, now - 60,
                       settings.rate_limit_per_minute, now, member))
    if count >= settings.rate_limit_per_minute:
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        retry_after = max(1, int(oldest[0][1] + 60 - now + 0.999)) if oldest else 60
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": str(retry_after)})
