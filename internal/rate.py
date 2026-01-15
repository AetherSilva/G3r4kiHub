import time
from .db import redis

class Limiter:
    def __init__(self, max_per_minute: int):
        self.max = max_per_minute

    async def allow(self, user_key: str, cost: int):
        r = redis()
        window = int(time.time()//60)
        key = f"credits_window:{user_key}:{window}"
        val = await r.incrby(key, cost)
        await r.expire(key, 120)
        if int(val) > self.max:
            return False, int(val)
        return True, int(val)
