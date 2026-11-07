"""FastAPI main application entrypoint with localhost restriction middleware and routers."""

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.context import get_app_context
from app.api.routes_local import router as local_router
from app.api.routes_peer import router as peer_router
from app.api.websocket import router as ws_router

logger = logging.getLogger("peershare")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and graceful shutdown lifespan handler."""
    ctx = get_app_context()
    ctx.event_manager.set_loop(asyncio.get_running_loop())
    logger.info("PeerShare backend starting for device %s (%s)", ctx.device_name, ctx.device_id)
    yield
    logger.info("PeerShare backend shutting down...")
    await ctx.discovery_manager.close()
    ctx.session_manager.close_session()


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(
        title="PeerShare API",
        version="1.0.0",
        description="Laptop-to-laptop reliable file transfer system with live ARQ visualization.",
        lifespan=lifespan,
    )

    # CORS configuration for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Localhost-only security middleware for /api/* endpoints
    @app.middleware("http")
    async def localhost_only_middleware(request: Request, call_next):
        if request.url.path.startswith("/api"):
            client_host = request.client.host if request.client else ""
            if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"success": False, "message": "Access forbidden: /api/* is local only"},
                )
        return await call_next(request)

    # Register routers
    app.include_router(local_router)
    app.include_router(peer_router)
    app.include_router(ws_router)

    return app


app = create_app()

