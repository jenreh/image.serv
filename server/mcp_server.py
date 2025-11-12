import logging
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.server.auth.auth import AuthProvider
from fastmcp.utilities.types import Image
from pydantic import Field

from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import edit_image_impl, generate_image_impl
from server.backend.models import EditImageInput, GenerationInput
from server.backend.utils import generate_response

logger = logging.getLogger(__name__)


def get_mcp_server(
    generator: OpenAIImageGenerator,
    auth: AuthProvider | None = None,
) -> FastMCP[Any]:
    mcp = FastMCP(
        name="Image Generation and Editing Server",
        instructions=(
            "This server allows the creation of new images and the editing "
            "of existing images. Handles text-to-image generation using OpenAI's "
            "gpt-image-1 and FLUX models. Supports multiple output formats: MCP Image "
            "objects, markdown or Microsoft Adaptive Card JSON."
        ),
        auth=auth,
    )

    @mcp.tool(
        name="generate_image",
        tags={"image", "generation"},
        description=(
            "Create an image based on the prompt. Supports multiple output "
            "formats: MCP Image objects, markdown strings, or Adaptive Card JSON."
        ),
    )
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
        ] = "1024x1024",
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

        return await generate_response(
            image_url, response_format, enhanced_prompt, output_format
        )

    @mcp.tool(
        name="edit_image",
        tags={"image", "editing"},
        description=(
            "Edit existing images based on the prompt and the list of image URLs. "
            "Supports multiple output formats: MCP Image objects, markdown strings, "
            "or Adaptive Card JSON."
        ),
    )
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
        ] = "jpeg",
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

        return await generate_response(
            image_url, response_format, prompt, output_format
        )

    return mcp
