"""FastAPI application factory."""

from fastapi import FastAPI

from .errors import register_exception_handlers
from .routes import router


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI instance with routes and exception handlers

    Note:
        Lifespan is assigned in server.py after app creation to handle
        both MCP and REST API initialization.
    """
    app = FastAPI(
        title="Image Service API",
        description="REST API for image generation and editing",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Include routes with prefix and tags
    app.include_router(router, prefix="/api/v1", tags=["Image Service"])

    # Register exception handlers
    register_exception_handlers(app)

    return app
