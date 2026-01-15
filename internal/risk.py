from typing import Tuple
import asyncio
from .db import pool

class Level:
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

class Engine:
    def __init__(self):
        pass

    async def evaluate(self, user_id: int, velocity: int, similarity: float, churn: int) -> Tuple[int, float]:
        score = 0.0
        score += float(velocity) * 0.5
        score += similarity * 100.0
        score += float(churn) * 10.0
        if score < 30:
            lvl = Level.LOW
        elif score < 60:
            lvl = Level.MEDIUM
        elif score < 90:
            lvl = Level.HIGH
        else:
            lvl = Level.CRITICAL
        return lvl, multiplier(lvl)


def multiplier(level: int) -> float:
    if level == Level.LOW:
        return 1.0
    if level == Level.MEDIUM:
        return 1.25
    if level == Level.HIGH:
        return 1.5
    if level == Level.CRITICAL:
        return 2.0
    return 1.0

async def log_event(user_id: int, device_id: str, event_type: str, details: dict):
    p = pool()
    async with p.acquire() as conn:
        await conn.execute("INSERT INTO abuse_log (user_id, device_id, event_type, details) VALUES ($1,$2,$3,$4)", user_id, device_id, event_type, details)
