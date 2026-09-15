import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.channels import router as channels_router
from app.api.routes.fetch_runs import router as fetch_runs_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resolver import router as resolver_router
from app.api.routes.telegram import router as telegram_router
from app.config import FRONTEND_URL
from app.services import telegram_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


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
app.include_router(channels_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(resolver_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(fetch_runs_router, prefix="/api")


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    # Raised when a dependency (Supabase, Telegram) isn't configured yet;
    # surface it as a clean 503 instead of an unhandled 500 with a traceback.
    return JSONResponse(status_code=503, content={"detail": str(exc)})
