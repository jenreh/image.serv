"""REST API routes for image generation and editing."""

import json
import logging
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
from server.backend.utils import generate_response

from .models import (
    ErrorDetail,
    ImageData,
    ImageResponse,
    ResponseMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_success_response(
    response_obj: str | object,
    response_format: str,
    prompt: str,
    size: str,
    processing_time_ms: int,
    enhanced_prompt: str | None = None,
) -> ImageResponse:
    """Build success response with formatted data and metadata.

    Args:
        response_obj: Formatted response object from generate_response
        response_format: Requested format ("image", "adaptive_card", or "markdown")
        prompt: Original prompt
        model: Model used
        size: Image size
        quality: Image quality
        user: User identifier
        processing_time_ms: Processing time in milliseconds
        enhanced_prompt: Enhanced/refined prompt if available

    Returns:
        ImageResponse with success status
    """
    # Format response data based on format type
    if response_format == "image":
        image_data = ImageData(images=[response_obj.data])
    elif response_format == "adaptive_card":
        image_data = ImageData(adaptive_card=json.loads(response_obj))
    else:
        image_data = ImageData(markdown=response_obj)

    # Build metadata
    metadata = ResponseMetadata(
        prompt=prompt,
        size=size,
        response_format=response_format,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),  # noqa: UP017
        processing_time_ms=processing_time_ms,
        enhanced_prompt=enhanced_prompt,
    )

    logger.debug("Operation successful - time: %d ms", processing_time_ms)

    return ImageResponse(
        status="success",
        data=image_data,
        metadata=metadata,
        error=None,
    )


def _error_response(
    prompt: str,
    model: str,
    size: str,
    quality: str,
    user: str,
    response_format: str,
    code: str,
    message: str,
    details: str = "",
) -> ImageResponse:
    """Build error response.

    Args:
        prompt: Original prompt
        model: Model used
        size: Image size
        quality: Image quality
        user: User identifier
        response_format: Response format
        code: Error code
        message: Error message
        details: Error details

    Returns:
        ImageResponse with error status
    """
    metadata = _build_response_metadata(
        prompt, model, size, quality, user, response_format, 0
    )
    return ImageResponse(
        status="error",
        data=None,
        metadata=metadata,
        error=ErrorDetail(code=code, message=message, details=details),
    )


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
        "REST API: Generating image - format: %s",
        request.response_format,
    )

    try:
        image_url, enhanced_prompt = await generate_image_impl(request, generator)
        response_obj = await generate_response(
            image_url, request.response_format, request.prompt
        )

        processing_time_ms = int((time.time() - start_time) * 1000)
        return _build_success_response(
            response_obj,
            request.response_format,
            request.prompt,
            request.size,
            processing_time_ms,
            enhanced_prompt,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during generation: %s", e)
        return _error_response(
            request.prompt,
            request.size,
            request.response_format,
            "INTERNAL_ERROR",
            "Internal server error",
            str(e),
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
        "REST API: Editing images - format: %s",
        request.response_format,
    )

    try:
        image_url = await edit_image_impl(request, generator)
        response_obj = await generate_response(
            image_url, request.response_format, request.prompt
        )

        processing_time_ms = int((time.time() - start_time) * 1000)
        return _build_success_response(
            response_obj,
            request.response_format,
            request.prompt,
            request.size,
            processing_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during editing: %s", e)
        return _error_response(
            request.prompt,
            request.size,
            request.response_format,
            "INTERNAL_ERROR",
            "Internal server error",
            str(e),
        )
