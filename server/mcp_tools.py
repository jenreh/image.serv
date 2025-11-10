"""Image generation tool for FastMCP server.

Handles text-to-image generation using OpenAI's gpt-image-1 and FLUX models.
Supports multiple output formats: MCP Image objects or Adaptive Card JSON.
"""

import logging
from typing import Annotated, Literal

from fastmcp.utilities.types import Image
from pydantic import Field

from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import edit_image_impl, generate_image_impl
from server.backend.models import EditImageInput, GenerationInput
from server.backend.utils import generate_response

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
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(
                description=(
                    "Image dimensions: 1024x1024 (square), "
                    "1536x1024 (landscape), 1024x1536 (portrait), or auto"
                )
            ),
        ],
        background: Annotated[
            Literal["transparent", "opaque", "auto"],
            Field(description="Background transparency setting"),
        ] = "auto",
        response_format: Annotated[
            Literal["image", "markdown", "adaptive_card"],
            Field(
                description=(
                    "Output format: 'image' for MCP Image objects, "
                    "'markdown' for markdown string with image link, "
                    "'adaptive_card' for Microsoft Adaptive Card JSON"
                )
            ),
        ] = "image",
        seed: Annotated[
            int,
            Field(description="Random seed for reproducibility (0 = random)"),
        ] = 0,
        enhance_prompt: Annotated[
            bool,
            Field(description="Auto-enhance prompt for better results"),
        ] = True,
        output_format: Annotated[
            Literal["png", "jpeg", "webp"],
            Field(description="Output image format"),
        ] = "jpeg",
    ) -> str | Image:
        """Generate image from text prompt using gpt-image-1 or FLUX.1-Kontext-pro.

        Returns the URL of the generated image.

        Supported models:
        - gpt-image-1: OpenAI's latest image generation model
        - FLUX.1-Kontext-pro: Black Forrest Labs model, preferred for
          photorealistic images
        """
        input_data = GenerationInput(
            prompt=prompt,
            size=size,
            output_format=output_format,
            background=background,
            response_format=response_format,
            seed=seed,
            enhance_prompt=enhance_prompt,
        )
        image_url, enhanced_prompt = await generate_image_impl(input_data, generator)

        return generate_response(image_url, response_format, enhanced_prompt)

    # Set tool metadata
    generate_image.__name__ = "generate_image"
    generate_image.__doc__ = (
        "Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro."
    )

    return generate_image


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
                    "List of image URLs, file paths, or base64 data URLs "
                    "to edit. Supports up to 4 images. "
                    "Formats: PNG, JPEG, WEBP (each <20MB)."
                )
            ),
        ],
        size: Annotated[
            Literal["1024x1024", "1536x1024", "1024x1536", "auto"],
            Field(description="Output image dimensions"),
        ] = "auto",
        output_format: Annotated[
            Literal["png", "jpeg", "webp"],
            Field(description="Output image format"),
        ] = "png",
        response_format: Annotated[
            Literal["image", "markdown", "adaptive_card"],
            Field(
                description=(
                    "Output format: 'image' for MCP Image objects, "
                    "'markdown' for markdown string with image link, "
                    "'adaptive_card' for Microsoft Adaptive Card JSON"
                )
            ),
        ] = "image",
    ) -> str | Image:
        """Edit existing images with text prompts and optional masks.

        Returns the URL of the edited image.

        Supports:
        - Multi-image editing (up to 16 images)
        - Inpainting with mask (transparent areas indicate edit zones)
        - Various output formats (PNG, JPEG, WEBP)

        Note: Only gpt-image-1 supports image editing.
        """
        input_data = EditImageInput(
            prompt=prompt,
            image_paths=image_paths,
            size=size,
            output_format=output_format,
        )
        image_url = await edit_image_impl(input_data, generator)

        return generate_response(image_url, response_format, prompt)

    # Set tool metadata
    edit_image.__name__ = "edit_image"
    edit_image.__doc__ = "Edit existing images with text prompts and optional masks."

    return edit_image
