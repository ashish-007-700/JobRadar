from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.config import FRONTEND_URL
from app.services import telegram_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await telegram_client.connect()
    except Exception:
        # Telegram may be unconfigured or temporarily unreachable; the app
        # should still start, and /api/health/telegram reports the real state.
        pass
    yield
    await telegram_client.disconnect()


app = FastAPI(title="JobRadar API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
