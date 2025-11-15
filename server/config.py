"""Configuration constants for the image generation server."""

from typing import Final

GENERATOR_ID: Final[str] = "azure"
MAX_IMAGES_TO_KEEP: Final[int] = 50

__all__ = ["GENERATOR_ID", "MAX_IMAGES_TO_KEEP"]
