"""Utility functions for image tool operations."""

import base64
import logging

import anyio
import httpx

logger = logging.getLogger(__name__)


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
        # Download from URL
        async with httpx.AsyncClient() as client:
            response = await client.get(url_or_path)
            response.raise_for_status()
            return base64.b64encode(response.content).decode()

    # Read from local file
    async with await anyio.open_file(url_or_path, "rb") as f:
        content = await f.read()
        return base64.b64encode(content).decode()
