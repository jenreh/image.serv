"""Unified server for MCP and REST API on single port.

Runs both FastMCP server and FastAPI with REST endpoints from a single
entry point using combined lifespan management.

Architecture:
- FastAPI is the primary ASGI server (runs on port 8000)
- MCP server is mounted as sub-application at /mcp
- Both share generator instance via app.state
- Combined lifespan manages startup/shutdown coordination

Endpoints:
- REST API: POST /api/v1/generate_image, /api/v1/edit_image
- MCP: POST /mcp/ (MCP protocol)
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP

from server.api.main import create_app
from server.backend.generators import OpenAIImageGenerator
from server.tools import create_edit_image_tool, create_generate_image_tool

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


async def init_generators() -> dict[str, OpenAIImageGenerator]:
    """Initialize generators from environment variables.

    Returns:
        Dictionary of initialized generators
    """
    generators: dict[str, OpenAIImageGenerator] = {}

    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL")
    google_key = os.environ.get("GOOGLE_API_KEY")
    backend_server = os.environ.get("BACKEND_SERVER")

    if openai_key and openai_base_url:
        generators["gpt-image-1"] = OpenAIImageGenerator(
            api_key=openai_key,
            base_url=openai_base_url,
            backend_server=backend_server,
            model="gpt-image-1",
        )
        logger.info("Initialized gpt-image-1 generator")

        generators["FLUX.1-Kontext-pro"] = OpenAIImageGenerator(
            api_key=google_key,
            backend_server=backend_server,
        )
        logger.info("Initialized FLUX.1-Kontext-pro generator")

    if not generators:
        logger.warning("No generators initialized - check environment variables")

    return generators


def create_mcp_server(
    generators: dict[str, OpenAIImageGenerator],
) -> FastMCP:
    """Create and configure MCP server with tools.

    Args:
        generators: Dictionary of initialized generators

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(name="Image Generation Server")

    if not generators.get("gpt-image-1"):
        logger.error("Cannot register MCP tools: gpt-image-1 generator not available")
        return mcp

    generator = generators["gpt-image-1"]

    # Register generation tool
    generate_tool = create_generate_image_tool(generator)
    mcp.tool(generate_tool)
    logger.info("Registered MCP generate_image tool")

    # Register editing tool
    edit_tool = create_edit_image_tool(generator)
    mcp.tool(edit_tool)
    logger.info("Registered MCP edit_image tool")

    return mcp


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Combined lifespan manager for FastAPI and MCP.

    Handles startup and shutdown of both REST API and MCP server.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # ===== STARTUP =====
    logger.info("Starting unified server...")

    # Initialize generators
    generators = await init_generators()
    app.state.generators = generators

    # Create and configure MCP server
    mcp = create_mcp_server(generators)
    app.state.mcp = mcp

    # Create MCP ASGI app
    mcp_app = mcp.http_app(path="/mcp")
    logger.info("Created MCP ASGI app at /mcp")

    # Mount MCP as sub-application
    app.mount("/mcp", mcp_app)

    logger.info("Mounted MCP server - unified server ready on port 8000")
    logger.info("Available endpoints: REST /api/v1/*, MCP /mcp/")

    yield  # Server runs here

    # ===== SHUTDOWN =====
    logger.info("Shutting down unified server...")
    logger.info("Cleanup complete")


def create_unified_app() -> FastAPI:
    """Create FastAPI application with combined lifespan.

    Returns:
        FastAPI application instance
    """
    app = create_app()
    app.lifespan = lifespan
    return app


def main() -> None:
    """Run unified server with both FastAPI and MCP.

    Starts a single Uvicorn server on port 8000 with:
    - FastAPI REST endpoints at /api/v1/*
    - MCP protocol endpoint at /mcp/
    """
    logger.info("Creating unified server...")
    app = create_unified_app()

    logger.info("Starting Uvicorn server on 0.0.0.0:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
