import os
import asyncio
import pytest
from datetime import timedelta

from internal.db import init_db, close_db
from internal.credits import issue_credits, get_balance, reserve, finalize, refund


@pytest.mark.asyncio
async def test_ledger_and_escrow():
    os.environ.setdefault('DATABASE_URL', 'postgres://postgres:postgres@localhost:5432/telegram_hub?sslmode=disable')
    await init_db()
    try:
        # create a user row (requires users table)
        pool = __import__('internal.db', fromlist=['pool']).pool()
        async with pool.acquire() as conn:
            r = await conn.fetchrow("INSERT INTO users (telegram_id, region, tier) VALUES ($1,$2,$3) RETURNING id", 9999999, 'IN', 'free')
            user_id = r['id']
        await issue_credits(user_id, 100, 'paid', 'test')
        bal = await get_balance(user_id)
        assert bal >= 100
        esc = await reserve(user_id, 30, 'test:escrow', 30)
        await finalize(esc)
        esc2 = await reserve(user_id, 20, 'test:escrow2', 30)
        await refund(esc2)
    finally:
        await close_db()
