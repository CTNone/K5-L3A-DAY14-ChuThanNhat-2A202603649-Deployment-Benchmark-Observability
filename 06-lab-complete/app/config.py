"""Application settings loaded from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    agent_api_key: str = os.getenv("AGENT_API_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rate_limit_per_minute: int = max(1, int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    daily_budget_usd: float = max(0.0, float(os.getenv("DAILY_BUDGET_USD", "1.0")))
    monthly_budget_usd: float = max(0.0, float(os.getenv("MONTHLY_BUDGET_USD", "0")))


settings = Settings()
