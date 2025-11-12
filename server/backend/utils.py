"""Utility functions for image tool operations."""

import base64
import logging
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import anyio
import httpx
from fastmcp.utilities.types import Image

from server.backend.adaptive_cards import image_card
from server.backend.models import TMP_PATH

logger = logging.getLogger(__name__)


async def generate_response(
    image_url: str,
    response_format: Literal["image", "markdown", "adaptive_card"],
    prompt: str,
    output_format: Literal["png", "jpeg", "webp"] = "jpeg",
) -> str | Image:
    """Generate response based on requested format.

    Args:
        image_url: URL of the generated/edited image
        response_format: "image", "markdown", or "adaptive_card"
        prompt: Original prompt (used for adaptive card and markdown)
        output_format: Image format (png, jpeg, webp)

    Returns:
        MCP Image object, Adaptive Card JSON string, or markdown string

    Raises:
        ValueError: If image URL conversion fails
    """
    if response_format == "image":
        try:
            image_bytes = await url_to_bytes(image_url)
            return Image(data=image_bytes, format=output_format)
        except Exception as e:
            logger.error("Failed to create Image object from URL: %s", str(e))
            raise ValueError(f"Failed to convert image URL to MCP Image: {e}") from e

    if response_format == "adaptive_card":
        return image_card(prompt, image_url)

    if response_format == "markdown":
        return f"![Generated Image]({image_url})\n\n**Prompt:** {prompt}"

    raise ValueError(f"Unknown response format: {response_format}")


async def url_to_bytes(url_or_path: str) -> bytes:
    """Load image from URL, file path, or data URL as bytes.

    Args:
        url_or_path: URL, file path, or base64 data URL

    Returns:
        Image data as bytes

    Raises:
        httpx.HTTPError: If download fails
        OSError: If file reading fails
    """
    # Handle data URLs
    if url_or_path.startswith("data:image"):
        base64_part = url_or_path.split(",", 1)[1]
        return base64.b64decode(base64_part)

    # Handle HTTP URLs
    if url_or_path.startswith(("http://", "https://")):
        parsed_url = urlparse(url_or_path)

        # Try local upload directory first
        if parsed_url.path.startswith("/_upload/"):
            local_path = Path(TMP_PATH) / Path(parsed_url.path).name
            if local_path.exists():
                logger.debug("Reading image from local path: %s", local_path)
                async with await anyio.open_file(local_path, "rb") as f:
                    return await f.read()

        # Fall back to remote download
        logger.debug("Downloading image from URL: %s", url_or_path)
        async with httpx.AsyncClient() as client:
            response = await client.get(url_or_path)
            response.raise_for_status()
            return response.content

    # Handle local file paths
    async with await anyio.open_file(url_or_path, "rb") as f:
        return await f.read()


async def url_to_base64(url_or_path: str) -> str:
    """Convert URL, file path, or data URL to base64 string.

    Args:
        url_or_path: URL, file path, or base64 data URL

    Returns:
        Base64 encoded string

    Raises:
        httpx.HTTPError: If download fails
        OSError: If file reading fails
    """
    content = await url_to_bytes(url_or_path)
    return base64.b64encode(content).decode()
