"""FastMCP server for image generation and editing with gpt-image-1.

Provides two tools:
- generate_image: Generate new images from text prompts
- edit_image: Edit existing images with prompts and optional masks

Optimized for gpt-image-1 model only.
"""

import base64
import logging
import os
from typing import Annotated, Literal

import anyio
import httpx
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from pydantic import Field

from app.backend.generators import GoogleImageGenerator, OpenAIImageGenerator
from app.backend.models import EditImageInput, GenerationInput, ImageResponseState

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(name="Image Generation Server")

# Initialize generators from environment
_generators = {}
_generators_initialized = False


def _init_generators():
    """Initialize generators from environment variables (lazy initialization)."""
    global _generators_initialized
    if _generators_initialized:
        return

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

    if google_key:
        _generators["FLUX.1-Kontext-pro"] = GoogleImageGenerator(
            api_key=google_key,
            backend_server=backend_server,
        )
        logger.info("Initialized FLUX.1-Kontext-pro generator")

    if not _generators:
        logger.warning("No generators initialized - check environment variables")

    _generators_initialized = True


async def _generate_image(
    prompt: str,
    model: Literal["gpt-image-1", "FLUX.1-Kontext-pro"] = "gpt-image-1",
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    user: str = "default",
) -> str:
    """Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro.

    Returns markdown with base64-encoded images embedded as data URLs.
    Images are always returned in base64 format for gpt-image-1.

    Supported models:
    - gpt-image-1: OpenAI's latest image generation model (supports editing)
    - FLUX.1-Kontext-pro: Google's Imagen model (generation only)
    """
    logger.info(
        "Generating image - user: %s, model: %s, n: %d, size: %s, quality: %s",
        user,
        model,
        n,
        size,
        quality,
    )

    # Lazy initialization of generators
    _init_generators()

    generator = _generators.get(model)
    if not generator:
        logger.error("Model not available: %s", model)
        return f"❌ **Error:** Model `{model}` is not available. Check environment."

    input_data = GenerationInput(
        prompt=prompt,
        model=model,
        size=size,
        quality=quality,
        n=n,
        user=user,
    )

    response = await generator.generate(input_data)

    if response.state == ImageResponseState.FAILED:
        logger.error("Image generation failed: %s", response.error)
        return f"❌ **Error:** {response.error}"

    # Convert images to base64 markdown
    markdown_parts = [
        f"# 🎨 Generated {len(response.images)} Image(s)\n\n",
        f"**Prompt:** {prompt}\n\n",
        f"**Model:** `{model}` | **Size:** `{size}` | **Quality:** `{quality}`\n\n",
        "---\n",
    ]

    for i, img_url in enumerate(response.images, 1):
        try:
            image_base64 = await _url_to_base64(img_url)
            markdown_parts.append(
                f"\n## Image {i}\n\n"
                f"![Generated Image {i}](data:image/png;base64,{image_base64})\n\n"
            )
        except Exception as e:
            logger.exception("Failed to encode image %d", i)
            markdown_parts.append(
                f"\n## Image {i}\n\n❌ **Error encoding image:** {e}\n\n"
            )

    logger.info(
        "Successfully generated %d images for user: %s", len(response.images), user
    )
    return "".join(markdown_parts)


# MCP tool wrapper for generate_image
@mcp.tool
async def generate_image(
    prompt: Annotated[
        str,
        Field(description="Text description of the desired image (max 32000 chars)"),
    ],
    model: Annotated[
        Literal["gpt-image-1", "FLUX.1-Kontext-pro"],
        Field(description="Model to use for generation"),
    ] = "gpt-image-1",
    n: Annotated[
        int, Field(description="Number of images to generate", ge=1, le=10)
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
        str, Field(description="User identifier for monitoring and abuse detection")
    ] = "default",
    context: Context = None,
) -> str:
    """Generate images from text prompts using gpt-image-1 or FLUX.1-Kontext-pro.

    Returns markdown with base64-encoded images embedded as data URLs.
    Images are always returned in base64 format for gpt-image-1.

    Supported models:
    - gpt-image-1: OpenAI's latest image generation model (supports editing)
    - FLUX.1-Kontext-pro: Google's Imagen model (generation only)
    """
    return await _generate_image(prompt, model, n, size, quality, user)


async def _edit_image(
    prompt: str,
    image_paths: list[str],
    model: Literal["gpt-image-1"] = "gpt-image-1",
    mask_path: str | None = None,
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    output_format: Literal["png", "jpeg", "webp"] = "png",
    user: str = "default",
) -> str:
    """Edit existing images with text prompts and optional masks (gpt-image-1 only).

    Supports:
    - Multi-image editing (up to 16 images)
    - Inpainting with mask (transparent areas indicate edit zones)
    - Various output formats (PNG, JPEG, WEBP)

    Returns markdown with base64-encoded edited images.

    Note: Only gpt-image-1 supports image editing. Other models will return an error.
    """
    logger.info(
        "Editing images - user: %s, model: %s, input_images: %d, has_mask: %s",
        user,
        model,
        len(image_paths),
        mask_path is not None,
    )

    if model != "gpt-image-1":
        logger.error("Attempted to use unsupported model for editing: %s", model)
        return (
            f"❌ **Error:** Model `{model}` does not support image editing. "
            "Only `gpt-image-1` supports this feature."
        )

    # Lazy initialization of generators
    _init_generators()

    generator = _generators.get(model)
    if not generator:
        logger.error("Model not available: %s", model)
        return f"❌ **Error:** Model `{model}` is not available. Check environment."

    input_data = EditImageInput(
        prompt=prompt,
        image_paths=image_paths,
        mask_path=mask_path,
        model=model,
        size=size,
        quality=quality,
        output_format=output_format,
        n=n,
        user=user,
    )

    response = await generator.edit(input_data)

    if response.state == ImageResponseState.FAILED:
        logger.error("Image editing failed: %s", response.error)
        return f"❌ **Error:** {response.error}"

    # Convert images to base64 markdown
    mask_info = "**Mask:** Yes (inpainting)" if mask_path else "**Mask:** No"

    markdown_parts = [
        f"# ✨ Edited {len(response.images)} Image(s)\n\n",
        f"**Prompt:** {prompt}\n\n",
        f"**Model:** `{model}` | **Size:** `{size}` | ",
        f"**Quality:** `{quality}` | **Format:** `{output_format}`\n\n",
        f"**Source Images:** {len(image_paths)} | {mask_info}\n\n",
        "---\n",
    ]

    for i, img_url in enumerate(response.images, 1):
        try:
            image_base64 = await _url_to_base64(img_url)
            markdown_parts.append(
                f"\n## Edited Image {i}\n\n"
                f"![Edited Image {i}]"
                f"(data:image/{output_format};base64,{image_base64})\n\n"
            )
        except Exception as e:
            logger.exception("Failed to encode image %d", i)
            markdown_parts.append(
                f"\n## Edited Image {i}\n\n❌ **Error encoding image:** {e}\n\n"
            )

    logger.info(
        "Successfully edited and generated %d images for user: %s",
        len(response.images),
        user,
    )
    return "".join(markdown_parts)


# MCP tool wrapper for edit_image
@mcp.tool
async def edit_image(
    prompt: Annotated[
        str,
        Field(description="Text description of the desired edits (max 32000 chars)"),
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
        Literal["gpt-image-1"],
        Field(description="Model to use (only gpt-image-1 supports editing)"),
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
        int, Field(description="Number of edited variations to generate", ge=1, le=10)
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
        Literal["png", "jpeg", "webp"], Field(description="Output image format")
    ] = "png",
    user: Annotated[
        str, Field(description="User identifier for monitoring and abuse detection")
    ] = "default",
    context: Context = None,
) -> str:
    """Edit existing images with text prompts and optional masks (gpt-image-1 only).

    Supports:
    - Multi-image editing (up to 16 images)
    - Inpainting with mask (transparent areas indicate edit zones)
    - Various output formats (PNG, JPEG, WEBP)

    Returns markdown with base64-encoded edited images.

    Note: Only gpt-image-1 supports image editing. Other models will return an error.
    """
    return await _edit_image(
        prompt, image_paths, model, mask_path, n, size, quality, output_format, user
    )


async def _url_to_base64(url_or_path: str) -> str:
    """Convert URL, file path, or data URL to base64 string."""
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


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
