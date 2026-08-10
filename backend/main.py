"""
FastAPI application entry point.

Wires together:
  - CORS middleware
  - Static file serving 
  - All API routers (game, assets)
  - Startup / shutdown lifecycle hooks (DB init, Celery)
  - Health check endpoint
"""

from __future__ import annotations

import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.assets import router as assets_router
from api.events import router as events_router
from api.game import router as game_router
from assets.generator import ASSETS_DIR
from config import get_settings

# Logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG if get_settings().is_development else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
# Suppress verbose/debug logging for openai & httpcore (debug level triggers)
# a known Pydantic v2 bug where by_alias=None is passed instead of a bool.
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

# App
app = FastAPI(
    title="AI Dungeon Master API",
    description="Infinite Procedural Fantasy RPG powered by LLMs",
    version="0.3.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (Phase 4 asset images)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ASSETS_DIR.parent)), name="static")

# Routers
app.include_router(game_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")


# Lifecycle
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("🎮 AI Game Master API starting up...")
    logger.info("Environment: %s", settings.app_env)
    logger.info("Model: %s", settings.llm_model)

    try:
        from database import init_db
        await init_db()
        logger.info("✓ PostgreSQL ready")
    except Exception as exc:
        logger.warning("PostgreSQL unavailable (running without DB persistence): %s", exc)

    from assets.generator import MAPS_DIR, PORTRAITS_DIR
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("✓ Asset directories ready")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    try:
        from database import close_db
        await close_db()
    except Exception:
        pass
    logger.info("AI Game Master API shut down.")


# Health
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/", tags=["system"])
async def root():
    return {
        "message": "AI Dungeon Master API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level="debug" if settings.is_development else "info",
    )
