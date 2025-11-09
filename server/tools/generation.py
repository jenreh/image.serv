"""Image generation tool for FastMCP server.

Handles text-to-image generation using OpenAI's gpt-image-1 and FLUX models.
"""

import logging
from typing import Annotated, Literal

from pydantic import Field

from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import generate_image_impl

logger = logging.getLogger(__name__)


def create_generate_image_tool(
    generator: OpenAIImageGenerator,
) -> callable:
    """Create a generate_image tool function with captured generator instance.

    Args:
        generator: OpenAI image generator instance

    Returns:
        Tool function ready to be registered with FastMCP
    """

    async def generate_image(
        prompt: Annotated[
            str,
            Field(
                description="Text description of the desired image (max 32000 chars)"
            ),
        ],
        model: Annotated[
            Literal["gpt-image-1", "FLUX.1-Kontext-pro"],
            Field(description="Model to use for generation"),
        ] = "gpt-image-1",
        n: Annotated[
            int, Field(description="Number of images to generate", ge=1, le=4)
        ] = 1,
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(
                description=(
                    "Image dimensions: 1024x1024 (square), "
                    "1536x1024 (landscape), 1024x1536 (portrait), or auto"
                )
            ),
        ] = "auto",
        quality: Annotated[
            Literal["low", "medium", "high", "auto"],
            Field(description="Image quality level (auto recommended)"),
        ] = "auto",
        user: Annotated[
            str,
            Field(description="User identifier for monitoring and abuse detection"),
        ] = "default",
    ) -> str:
        """Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro.

        Returns markdown with base64-encoded images embedded as data URLs.
        Images are always returned in base64 format for gpt-image-1.

        Supported models:
        - gpt-image-1: OpenAI's latest image generation model (supports editing)
        - FLUX.1-Kontext-pro: Black Forrest Labs model (supports editing),
          preferred for photorealistic images
        """
        return await generate_image_impl(
            prompt, generator, model, n, size, quality, user
        )

    # Set tool metadata
    generate_image.__name__ = "generate_image"
    generate_image.__doc__ = (
        "Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro."
    )

    return generate_image
