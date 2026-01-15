import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from pydantic import BaseModel

from internal.db import init_db, init_redis, close_db, close_redis, pool, redis
from internal.credits import get_balance, append_entry, issue_credits, reserve, finalize, refund
from internal.risk import Engine
from internal.rate import Limiter
from internal.burn import BurnFactors, compute_burn

app = FastAPI()
rate_limiter = Limiter(100)
risk_engine = Engine()

class Update(BaseModel):
    update_id: int
    message: dict | None = None
    pre_checkout_query: dict | None = None

@app.on_event("startup")
async def startup():
    await init_db()
    await init_redis()

@app.on_event("shutdown")
async def shutdown():
    await close_db()
    await close_redis()

@app.post("/webhook")
async def webhook(update: Update, request: Request):
    # basic validation
    if update.message is None and update.pre_checkout_query is None:
        raise HTTPException(status_code=400, detail="no message")
    # if message with text command
    if update.message and 'text' in update.message:
        text = update.message['text']
        user = update.message.get('from', {})
        user_id = user.get('id', 0)
        # very simple command parsing
        if text.startswith('/ai chat'):
            args = text[len('/ai chat'):].strip()
            # compute burn
            bf = BurnFactors(base_cost=5, model_multiplier=1.0, size_factor=max(1, len(args)/20.0), risk_multiplier=1.0)
            cost = compute_burn(bf)
            allowed, window = await rate_limiter.allow(str(user_id), cost)
            if not allowed:
                return {"ok": False, "error": "rate_limited"}
            # create escrow
            try:
                esc = await reserve(user_id, cost, 'ai_chat', 60)
            except Exception as e:
                return {"ok": False, "error": str(e)}
            # deterministic reply (call local AI service would be here)
            reply = f"AI Chat reply (deterministic): {args[::-1]}"
            # finalize
            await finalize(esc)
            return {"ok": True, "reply": reply}
        return {"ok": False, "error": "unknown_command"}
    return {"ok": True}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
