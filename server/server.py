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
from typing import Literal

import uvicorn
from dotenv import load_dotenv
from fastmcp import FastMCP

from server.api.main import create_app
from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import edit_image_impl, generate_image_impl

# Load environment variables from .env file (explicit path for reliability)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()  # Fallback to automatic detection

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
_generators: dict[str, OpenAIImageGenerator] = {}


def init_generators() -> None:
    """Initialize generators from environment variables."""
    if _generators:
        return  # Already initialized

    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL")
    google_key = os.environ.get("GOOGLE_API_KEY")
    backend_server = os.environ.get("BACKEND_SERVER")

    if openai_key and openai_base_url:
        _generators["gpt-image-1"] = OpenAIImageGenerator(
            api_key=openai_key,
            base_url=openai_base_url,
            backend_server=backend_server,
            model="gpt-image-1",
        )
        logger.info("Initialized gpt-image-1 generator")

        _generators["FLUX.1-Kontext-pro"] = OpenAIImageGenerator(
            api_key=google_key,
            backend_server=backend_server,
        )
        logger.info("Initialized FLUX.1-Kontext-pro generator")

    if not _generators:
        logger.warning("✗ No generators initialized - check environment variables")


# Initialize generators
init_generators()

# Create MCP server
mcp = FastMCP(name="Image Generation Server")


@mcp.tool
async def generate_image(
    prompt: str,
    model: Literal["gpt-image-1", "FLUX.1-Kontext-pro"] = "gpt-image-1",
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    user: str = "default",
) -> str:
    """Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro.

    Args:
        prompt: Text description of the desired image (max 32000 chars)
        model: Model to use for generation (default: gpt-image-1)
        n: Number of images to generate (1-4, default: 1)
        size: Image dimensions (default: auto)
        quality: Image quality level (default: auto)
        user: User identifier for monitoring (default: "default")

    Returns:
        Markdown with base64-encoded images embedded as data URLs
    """
    if not _generators.get("gpt-image-1"):
        return "Error: No generator available. Check OPENAI_API_KEY configuration."

    generator = _generators["gpt-image-1"]
    markdown, _ = await generate_image_impl(
        prompt, generator, model, n, size, quality, user
    )
    return markdown


@mcp.tool
async def edit_image(
    prompt: str,
    image_paths: list[str],
    model: Literal["gpt-image-1", "FLUX.1-Kontext-pro"] = "gpt-image-1",
    mask_path: str | None = None,
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    output_format: Literal["png", "jpeg", "webp"] = "png",
    user: str = "default",
) -> str:
    """Edit existing images with text prompts and optional masks.

    Args:
        prompt: Text description of the desired edits (max 32000 chars)
        image_paths: List of image URLs, file paths, or base64 data URLs (up to 16)
        model: Model to use (default: gpt-image-1)
        mask_path: Optional mask image for inpainting (transparent areas = edit zones)
        n: Number of edited variations to generate (1-4, default: 1)
        size: Output image dimensions (default: auto)
        quality: Output image quality (default: auto)
        output_format: Output format - png, jpeg, or webp (default: png)
        user: User identifier for monitoring (default: "default")

    Returns:
        Markdown with base64-encoded edited images

    Note:
        - Only gpt-image-1 supports image editing
        - Mask must have same dimensions as input images
        - Fully transparent areas (alpha=0) indicate where to edit
    """
    if not _generators.get("gpt-image-1"):
        return "Error: No generator available. Check OPENAI_API_KEY configuration."

    generator = _generators["gpt-image-1"]
    return await edit_image_impl(
        prompt,
        image_paths,
        generator,
        model,
        mask_path,
        n,
        size,
        quality,
        output_format,
        user,
    )


# Create MCP ASGI app
logger.info("Creating MCP ASGI application...")
mcp_app = mcp.http_app(path="/mcp")
logger.info("✓ MCP app created with endpoint at /mcp")

# Create FastAPI app with MCP's lifespan
logger.info("Creating FastAPI application...")
app = create_app(lifespan=mcp_app.lifespan)
logger.info("✓ FastAPI app created")

# Store generators in app state for REST API
app.state.generators = _generators
app.state.mcp = mcp

# Mount MCP server
app.mount("/", mcp_app)
logger.info("✓ Mounted MCP server")

logger.info("=" * 60)
logger.info("Server configuration complete")
logger.info("  REST API:    /api/v1/*")
logger.info("  MCP:         /mcp")
logger.info("  Docs:        /api/docs")
logger.info("=" * 60)


def main() -> None:
    """Run unified server with both FastAPI and MCP.

    Starts a single Uvicorn server on port 8000 with:
    - FastAPI REST endpoints at /api/v1/*
    - MCP protocol endpoint at /mcp
    """
    logger.info("Starting Uvicorn server...")
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":
    main()
