"""Image editing tool for FastMCP server.

Handles image editing and inpainting using OpenAI's gpt-image-1 model.
"""

import logging
from typing import Annotated, Literal

from pydantic import Field

from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import edit_image_impl

logger = logging.getLogger(__name__)


def create_edit_image_tool(
    generator: OpenAIImageGenerator,
) -> callable:
    """Create an edit_image tool function with captured generator instance.

    Args:
        generator: OpenAI image generator instance

    Returns:
        Tool function ready to be registered with FastMCP
    """

    async def edit_image(
        prompt: Annotated[
            str,
            Field(
                description="Text description of the desired edits (max 32000 chars)"
            ),
        ],
        image_paths: Annotated[
            list[str],
            Field(
                description=(
                    "List of image URLs, file paths, or base64 data URLs to edit. "
                    "Supports up to 16 images for gpt-image-1. "
                    "Formats: PNG, JPEG, WEBP (each <50MB)."
                )
            ),
        ],
        model: Annotated[
            Literal["gpt-image-1", "FLUX.1-Kontext-pro"],
            Field(description="Model to use for generation"),
        ] = "gpt-image-1",
        mask_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional mask image (PNG) for inpainting. "
                    "Fully transparent areas (alpha=0) indicate where to edit. "
                    "Must have same dimensions as input images."
                )
            ),
        ] = None,
        n: Annotated[
            int,
            Field(description="Number of edited variations to generate", ge=1, le=4),
        ] = 1,
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(description="Output image dimensions"),
        ] = "auto",
        quality: Annotated[
            Literal["low", "medium", "high", "auto"],
            Field(description="Output image quality (auto recommended)"),
        ] = "auto",
        output_format: Annotated[
            Literal["png", "jpeg", "webp"],
            Field(description="Output image format"),
        ] = "png",
        user: Annotated[
            str,
            Field(description="User identifier for monitoring and abuse detection"),
        ] = "default",
    ) -> str:
        """Edit existing images with text prompts and optional masks.

        Supports:
        - Multi-image editing (up to 16 images)
        - Inpainting with mask (transparent areas indicate edit zones)
        - Various output formats (PNG, JPEG, WEBP)

        Returns markdown with base64-encoded edited images.

        Note: Only gpt-image-1 supports image editing. Other models will
        return an error.
        """
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

    # Set tool metadata
    edit_image.__name__ = "edit_image"
    edit_image.__doc__ = "Edit existing images with text prompts and optional masks."

    return edit_image
