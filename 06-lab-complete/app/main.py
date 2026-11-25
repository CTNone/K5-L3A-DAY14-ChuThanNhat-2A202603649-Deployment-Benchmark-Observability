"""Production ready mock AI agent API."""
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                           "lvl": record.levelname, "event": record.getMessage()},
                          ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("startup environment=%s", settings.environment)
    yield
    logger.info("shutdown complete")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = None


@app.middleware("http")
async def request_logging(request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request path=%s status=500", request.url.path)
        raise
    logger.info("request path=%s status=%d ms=%.2f", request.url.path,
                response.status_code, (time.perf_counter() - started) * 1000)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        return JSONResponse(status_code=503, content={"status": "not_ready", "redis": False})
    return {"status": "ready", "redis": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    try:
        check_rate_limit(api_key)
        check_budget()
        answer = llm_ask(body.question)
        input_tokens = max(1, len(body.question) // 4)
        output_tokens = max(1, len(answer) // 4)
        cost = record_cost(input_tokens, output_tokens)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("backend operation failed")
        raise HTTPException(status_code=503, detail="Backend unavailable") from exc
    return {"question": body.question, "answer": answer, "cost_usd": cost}
