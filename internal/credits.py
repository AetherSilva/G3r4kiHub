import asyncio
import time
from typing import Optional
import uuid
import os

from datetime import datetime, timezone
from .db import pool


async def get_balance(user_id: int) -> int:
    p = pool()
    row = await p.fetchrow("SELECT COALESCE((SELECT balance_after FROM ledger WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1),0) as bal", user_id)
    return int(row['bal']) if row else 0

async def append_entry(user_id: int, delta: int, source: str, reason: str):
    p = pool()
    async with p.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT COALESCE((SELECT balance_after FROM ledger WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1),0) as bal", user_id)
            last_bal = int(row['bal']) if row else 0
            new_bal = last_bal + delta
            if new_bal < 0:
                raise ValueError("insufficient balance")
            r = await conn.fetchrow("INSERT INTO ledger (user_id, change, source, reason, balance_after) VALUES ($1,$2,$3,$4,$5) RETURNING id, created_at", user_id, delta, source, reason, new_bal)
            return {
                'id': r['id'],
                'user_id': user_id,
                'change': delta,
                'source': source,
                'reason': reason,
                'balance_after': new_bal,
                'created_at': r['created_at']
            }

async def issue_credits(user_id: int, amount: int, source: str, reason: str):
    if amount <= 0:
        raise ValueError("amount must be > 0")
    return await append_entry(user_id, amount, source, reason)


async def reserve(user_id: int, amount: int, reason: str, ttl_seconds: int = 3600):
    if amount <= 0:
        raise ValueError("amount must be > 0")
    p = pool()
    esc_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    async with p.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT COALESCE((SELECT balance_after FROM ledger WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1),0) as bal", user_id)
            last_bal = int(row['bal']) if row else 0
            if last_bal < amount:
                raise ValueError("insufficient balance for escrow")
            await conn.execute("INSERT INTO ledger (user_id, change, source, reason, balance_after) VALUES ($1,$2,$3,$4,$5)", user_id, -amount, 'paid', f'escrow:{reason}', last_bal - amount)
            await conn.execute("INSERT INTO escrow (id, user_id, reserved, reason, expires_at) VALUES ($1,$2,$3,$4,$5)", esc_id, user_id, amount, reason, expires_at)
    return esc_id

from datetime import timedelta

async def finalize(esc_id: str):
    p = pool()
    async with p.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT user_id, reserved FROM escrow WHERE id=$1", esc_id)
            if not row:
                raise ValueError("escrow not found")
            await conn.execute("DELETE FROM escrow WHERE id=$1", esc_id)
    return True

async def refund(esc_id: str):
    p = pool()
    async with p.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT user_id, reserved FROM escrow WHERE id=$1", esc_id)
            if not row:
                raise ValueError("escrow not found")
            user_id = row['user_id']
            reserved = row['reserved']
            last = await conn.fetchrow("SELECT COALESCE((SELECT balance_after FROM ledger WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1),0) as bal", user_id)
            last_bal = int(last['bal']) if last else 0
            new_bal = last_bal + reserved
            await conn.execute("INSERT INTO ledger (user_id, change, source, reason, balance_after) VALUES ($1,$2,$3,$4,$5)", user_id, reserved, 'paid', f'escrow_refund:{esc_id}', new_bal)
            await conn.execute("DELETE FROM escrow WHERE id=$1", esc_id)
    return True
