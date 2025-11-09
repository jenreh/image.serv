"""Image editing tool for FastMCP server.

Handles image editing and inpainting using OpenAI's gpt-image-1 model.
"""

import logging
from typing import Literal

from server.backend.generators import OpenAIImageGenerator
from server.backend.models import EditImageInput, GenerationInput, ImageResponseState

from .utils import url_to_base64

logger = logging.getLogger(__name__)


async def edit_image_impl(
    prompt: str,
    image_paths: list[str],
    generator: OpenAIImageGenerator,
    model: Literal["gpt-image-1", "FLUX.1-Kontext-pro"] = "gpt-image-1",
    mask_path: str | None = None,
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    output_format: Literal["png", "jpeg", "webp"] = "png",
    user: str = "default",
) -> str:
    """Edit existing images with text prompts and optional masks.

    Supports multi-image editing and inpainting with masks.

    Args:
        prompt: Text description of desired edits
        image_paths: List of image paths or URLs
        generator: OpenAI image generator instance
        model: Model to use for editing
        mask_path: Optional mask image path for inpainting
        n: Number of edited variations to generate
        size: Output image dimensions
        quality: Output quality level
        output_format: Output image format
        user: User identifier for tracking

    Returns:
        Markdown formatted response with edited images or error message
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
            image_base64 = await url_to_base64(img_url)
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


async def generate_image_impl(
    prompt: str,
    generator: OpenAIImageGenerator,
    model: Literal["gpt-image-1", "FLUX.1-Kontext-pro"] = "gpt-image-1",
    n: int = 1,
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
    quality: Literal["low", "medium", "high", "auto"] = "auto",
    user: str = "default",
) -> str:
    """Generate images from text prompts using specified model.

    Returns markdown with base64-encoded images embedded as data URLs.

    Args:
        prompt: Text description of desired image
        generator: OpenAI image generator instance
        model: Model to use for generation
        n: Number of images to generate
        size: Image dimensions
        quality: Output quality level
        user: User identifier for tracking

    Returns:
        Markdown formatted response with embedded images or error message
    """
    logger.info(
        "Generating image - user: %s, model: %s, n: %d, size: %s, quality: %s",
        user,
        model,
        n,
        size,
        quality,
    )

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
            image_base64 = await url_to_base64(img_url)
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
