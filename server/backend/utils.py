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
) -> str | Image:
    """Generate response based on requested format.

    Args:
        image_url: URL of the generated/edited image
        response_format: Desired response format
        prompt: Original prompt (used for adaptive card and markdown)

    Returns:
        MCP Image object, Adaptive Card JSON string, or markdown string

    Raises:
        ValueError: If image URL conversion fails
    """
    if response_format == "image":
        # Convert URL to base64 and return MCP Image object
        try:
            image_base64 = await url_to_base64(image_url)
            return Image(data=image_base64, mimeType="image/png")
        except Exception as e:
            logger.error("Failed to create Image object from URL: %s", str(e))
            raise ValueError(f"Failed to convert image URL to MCP Image: {e}") from e

    elif response_format == "adaptive_card":
        # Return Adaptive Card JSON
        return image_card(prompt, image_url)

    elif response_format == "markdown":
        # Return markdown with image link
        return f"![Generated Image]({image_url})\n\n**Prompt:** {prompt}"

    else:
        raise ValueError(f"Unknown response format: {response_format}")


async def url_to_base64(url_or_path: str) -> str:
    """Convert URL, file path, or data URL to base64 string.

    Args:
        url_or_path: URL, file path, or base64 data URL to convert

    Returns:
        Base64 encoded string

    Raises:
        httpx.HTTPError: If URL download fails
        OSError: If file reading fails
    """
    if url_or_path.startswith("data:image"):
        # Already base64 data URL, extract the base64 part
        return url_or_path.split(",", 1)[1]

    if url_or_path.startswith(("http://", "https://")):
        parsed_url = urlparse(url_or_path)

        if parsed_url.path.startswith("/_upload/"):
            local_filename = Path(parsed_url.path).name
            local_path = Path(TMP_PATH) / local_filename

            if local_path.exists():
                logger.debug(
                    "Reading generated image file %s from local path %s",
                    url_or_path,
                    local_path,
                )
                async with await anyio.open_file(local_path, "rb") as f:
                    content = await f.read()
                    return base64.b64encode(content).decode()

            logger.debug(
                "Generated image file %s not found at %s, falling back to HTTP",
                url_or_path,
                local_path,
            )

        # Download from remote URL or when local file was not found
        async with httpx.AsyncClient() as client:
            response = await client.get(url_or_path)
            response.raise_for_status()
            return base64.b64encode(response.content).decode()

    # Read from local file
    async with await anyio.open_file(url_or_path, "rb") as f:
        content = await f.read()
        return base64.b64encode(content).decode()
