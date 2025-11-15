"""Unified server for MCP and REST API on single port.

Runs both FastMCP server and FastAPI with REST endpoints from a single
entry point using combined lifespan management.

Architecture:
- FastMCP server handles image generation and editing tools
- FastAPI is the primary ASGI server (runs on port 8000)
- MCP server is mounted as sub-application with its own lifespan
- Both share generator instances via app.state

Endpoints:
- REST API: POST /api/v1/generate_image, /api/v1/edit_image
- MCP: POST /mcp (streamable HTTP protocol)
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Final

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.errors import register_exception_handlers
from server.api.routes import router
from server.backend.generators import OpenAIImageGenerator
from server.backend.models import ImageGenerator
from server.config import GENERATOR_ID
from server.mcp_server import get_mcp_server

_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()  # Fallback to automatic detection

TMP_PATH: Final[str] = os.environ.get("TMP_PATH", "../images")
PORT: Final[int] = int(os.environ.get("PORT", "8000"))

# Configure logging to project directory (NOT /tmp/)
_logs_dir = Path(__file__).parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(_logs_dir / "server.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


# Initialize generators at module level
_generators: dict[str, ImageGenerator] = {}


def init_generators() -> None:
    """Initialize generators from environment variables."""
    if _generators:
        return  # Already initialized

    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL")
    backend_server = os.environ.get("BACKEND_SERVER")

    if openai_key and openai_base_url:
        _generators[GENERATOR_ID] = OpenAIImageGenerator(
            api_key=openai_key,
            base_url=openai_base_url,
            backend_server=backend_server,
            # model="gpt-image-1",
            model="FLUX.1-Kontext-pro",
        )
        logger.info("Initialized Azure image generator")

    if not _generators:
        logger.warning("✗ No generators initialized - check environment variables")


init_generators()
mcp_server = get_mcp_server(generator=_generators.get(GENERATOR_ID))
mcp_app = mcp_server.http_app(
    stateless_http=True,
    path="/v1",
)

app = FastAPI(
    title="Image Service API",
    description="REST API for image generation and editing",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=mcp_app.lifespan,
)

# Add CORS middleware to handle preflight requests for MCP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", mcp_app)
app.include_router(router, prefix="/api/v1", tags=["image"])
register_exception_handlers(app)

# Store generators in app state for route handlers
app.state.generators = _generators

tmp_dir = Path(TMP_PATH)
tmp_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/_upload",
    StaticFiles(directory=str(tmp_dir.resolve()), check_dir=False),
    name="uploads",
)


def main() -> None:
    logger.info("Starting Uvicorn server...")

    logger.info("=" * 60)
    logger.info("Server configuration")
    logger.info("  MCP:         /mcp/v1")
    logger.info("  REST API:    /api/v1/*")
    logger.info("  Docs:        /api/docs")
    logger.info("=" * 60)

    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":
    main()
