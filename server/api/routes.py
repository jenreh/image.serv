"""REST API routes for image generation and editing."""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from server.backend.generators import OpenAIImageGenerator
from server.backend.image_service import (
    edit_image_impl,
    generate_image_impl,
)
from server.backend.models import EditImageInput, GenerationInput

from .errors import GenerationError
from .models import (
    ErrorDetail,
    ImageData,
    ImageResponse,
    ResponseMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_generator(request: Request) -> OpenAIImageGenerator:
    """Dependency to inject generator from app state.

    Args:
        request: FastAPI request object

    Returns:
        OpenAI image generator instance

    Raises:
        HTTPException: If generator not initialized
    """
    generator = getattr(request.app.state, "generators", {}).get("gpt-image-1")
    if not generator:
        logger.error("Generator not available in app state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image generator not initialized",
        )
    return generator


def extract_error_from_markdown(markdown: str) -> str | None:
    """Extract error message from markdown response.

    Args:
        markdown: Markdown string that may contain error

    Returns:
        Error message or None if no error
    """
    match = re.search(r"❌ \*\*Error:\*\* (.*?)(?:\n|$)", markdown)
    if match:
        return match.group(1)
    return None


@router.post("/generate_image")
async def generate_image_route(
    request: GenerationInput,
    generator: Annotated[OpenAIImageGenerator, Depends(get_generator)],
) -> ImageResponse:
    """Generate images from text prompt.

    Args:
        request: Generation request with prompt and parameters
        generator: Injected image generator

    Returns:
        ImageResponse with generated images and metadata

    Raises:
        HTTPException: On validation or generation errors
    """
    start_time = time.time()

    logger.info(
        "REST API: Generating image - user: %s, model: %s, n: %d",
        request.user,
        request.model,
        request.n,
    )

    try:
        # Call shared implementation
        markdown = await generate_image_impl(
            prompt=request.prompt,
            generator=generator,
            model=request.model,
            n=request.n,
            size=request.size,
            quality=request.quality,
            user=request.user,
        )

        # Check for errors in markdown
        error_msg = extract_error_from_markdown(markdown)
        if error_msg:
            logger.warning("Generation failed: %s", error_msg)
            raise GenerationError(error_msg)

        processing_time = (time.time() - start_time) * 1000

        metadata = ResponseMetadata(
            prompt=request.prompt,
            model=request.model,
            n=request.n,
            size=request.size,
            quality=request.quality,
            user=request.user,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),  # noqa: UP017
            processing_time_ms=int(processing_time),
        )

        logger.info(
            "Generation successful - user: %s, time: %d ms",
            request.user,
            int(processing_time),
        )

        return ImageResponse(
            status="success",
            data=ImageData(images=[], markdown=markdown),
            metadata=metadata,
            error=None,
        )

    except GenerationError as e:
        logger.warning("Generation error: %s", e.message)
        return ImageResponse(
            status="error",
            data=None,
            metadata=ResponseMetadata(
                prompt=request.prompt,
                model=request.model,
                n=request.n,
                size=request.size,
                quality=request.quality,
                user=request.user,
            ),
            error=ErrorDetail(code="GENERATION_FAILED", message=e.message, details=""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during generation: %s", e)
        return ImageResponse(
            status="error",
            data=None,
            metadata=ResponseMetadata(
                prompt=request.prompt,
                model=request.model,
                n=request.n,
                size=request.size,
                quality=request.quality,
                user=request.user,
            ),
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Internal server error",
                details=str(e),
            ),
        )


@router.post("/edit_image")
async def edit_image_route(
    request: EditImageInput,
    generator: Annotated[OpenAIImageGenerator, Depends(get_generator)],
) -> ImageResponse:
    """Edit images with text prompt and optional mask.

    Args:
        request: Edit request with prompt and image paths
        generator: Injected image generator

    Returns:
        ImageResponse with edited images and metadata

    Raises:
        HTTPException: On validation or editing errors
    """
    start_time = time.time()

    logger.info(
        "REST API: Editing images - user: %s, model: %s, images: %d",
        request.user,
        request.model,
        len(request.image_paths),
    )

    try:
        # Call shared implementation
        markdown = await edit_image_impl(
            prompt=request.prompt,
            image_paths=request.image_paths,
            generator=generator,
            model=request.model,
            mask_path=request.mask_path,
            n=request.n,
            size=request.size,
            quality=request.quality,
            output_format=request.output_format,
            user=request.user,
        )

        # Check for errors in markdown
        error_msg = extract_error_from_markdown(markdown)
        if error_msg:
            logger.warning("Editing failed: %s", error_msg)
            raise GenerationError(error_msg)

        processing_time = (time.time() - start_time) * 1000

        metadata = ResponseMetadata(
            prompt=request.prompt,
            model=request.model,
            n=request.n,
            size=request.size,
            quality=request.quality,
            user=request.user,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),  # noqa: UP017
            processing_time_ms=int(processing_time),
        )

        logger.info(
            "Editing successful - user: %s, time: %d ms",
            request.user,
            int(processing_time),
        )

        return ImageResponse(
            status="success",
            data=ImageData(images=[], markdown=markdown),
            metadata=metadata,
            error=None,
        )

    except GenerationError as e:
        logger.warning("Editing error: %s", e.message)
        return ImageResponse(
            status="error",
            data=None,
            metadata=ResponseMetadata(
                prompt=request.prompt,
                model=request.model,
                n=request.n,
                size=request.size,
                quality=request.quality,
                user=request.user,
            ),
            error=ErrorDetail(code="GENERATION_FAILED", message=e.message, details=""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during editing: %s", e)
        return ImageResponse(
            status="error",
            data=None,
            metadata=ResponseMetadata(
                prompt=request.prompt,
                model=request.model,
                n=request.n,
                size=request.size,
                quality=request.quality,
                user=request.user,
            ),
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Internal server error",
                details=str(e),
            ),
        )
