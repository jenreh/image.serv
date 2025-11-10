"""FastAPI application factory."""

from collections.abc import AsyncIterator, Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.backend.models import TMP_PATH

from .errors import register_exception_handlers
from .routes import router

Lifespan = Callable[[FastAPI], AsyncIterator[None]]


def create_app(*, lifespan: Lifespan | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI instance with routes and exception handlers

    Args:
        lifespan: Optional lifespan context manager for application startup/shutdown

    Note:
        When provided, lifespan is used to coordinate MCP and REST initialization.
    """
    app = FastAPI(
        title="Image Service API",
        description="REST API for image generation and editing",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Include routes with prefix and tags
    app.include_router(router, prefix="/api/v1", tags=["Image Service"])

    # Register exception handlers
    register_exception_handlers(app)

    # Serve generated images stored in TMP_PATH directory
    tmp_dir = Path(TMP_PATH)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/_upload",
        StaticFiles(directory=str(tmp_dir.resolve()), check_dir=False),
        name="uploads",
    )

    return app
