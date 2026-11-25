"""Redis backed daily or monthly LLM cost guard."""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _period(now: datetime) -> tuple[str, float, int]:
    if settings.monthly_budget_usd > 0:
        return now.strftime("%Y-%m"), settings.monthly_budget_usd, 32 * 24 * 60 * 60
    next_day = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400
    return now.strftime("%Y-%m-%d"), settings.daily_budget_usd, max(1, int(next_day - now.timestamp()))


def check_budget() -> None:
    period, budget, _ = _period(datetime.now(timezone.utc))
    current = float(r.get(f"cost:{period}") or 0)
    if current >= budget:
        raise HTTPException(status_code=402, detail="Budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (max(1, int(input_tokens)) * PRICE_INPUT_PER_1K
            + max(1, int(output_tokens)) * PRICE_OUTPUT_PER_1K) / 1000
    period, _, ttl = _period(datetime.now(timezone.utc))
    key = f"cost:{period}"
    pipe = r.pipeline()
    pipe.incrbyfloat(key, cost)
    pipe.expire(key, ttl)
    pipe.execute()
    return cost
