import os
import asyncio
from typing import Optional
import asyncpg
import aioredis

_pool: Optional[asyncpg.Pool] = None
_redis: Optional[aioredis.Redis] = None

async def init_db():
    global _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    _pool = await asyncpg.create_pool(dsn=url, min_size=1, max_size=10)

async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def get_conn():
    if _pool is None:
        await init_db()
    return _pool

async def init_redis():
    global _redis
    addr = os.getenv("REDIS_ADDR", "redis://localhost:6379")
    _redis = await aioredis.from_url(addr, encoding="utf-8", decode_responses=True)

async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None

def redis():
    if _redis is None:
        raise RuntimeError("redis not initialized")
    return _redis

def pool():
    if _pool is None:
        raise RuntimeError("db pool not initialized")
    return _pool
