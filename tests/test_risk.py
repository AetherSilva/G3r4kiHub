import pytest
import asyncio
from internal.risk import Engine, Level, multiplier

@pytest.mark.asyncio
async def test_risk_levels():
    e = Engine()
    lvl, mul = await e.evaluate(1, velocity=1, similarity=0.01, churn=0)
    assert lvl in (Level.LOW, Level.MEDIUM, Level.HIGH, Level.CRITICAL)
    assert mul == multiplier(lvl)

    lvl2, mul2 = await e.evaluate(1, velocity=500, similarity=0.9, churn=10)
    assert lvl2 == Level.CRITICAL
    assert mul2 == 2.0
