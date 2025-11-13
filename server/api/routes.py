"""REST API routes for image generation and editing."""

import json
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from server.backend.image_service import (
    edit_image_impl,
    generate_image_impl,
)
from server.backend.models import EditImageInput, GenerationInput, ImageGenerator
from server.backend.utils import generate_response
from server.server import GENERATOR_ID

from .models import (
    ErrorDetail,
    ImageData,
    ImageResponse,
    ResponseMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_image_data(response_obj: str | object, response_format: str) -> ImageData:
    """Format response data based on requested format.

    Args:
        response_obj: Formatted response object from generate_response
        response_format: Requested format ("image", "adaptive_card", or "markdown")

    Returns:
        ImageData with appropriate content
    """
    match response_format:
        case "image":
            return ImageData(images=[response_obj.data])
        case "adaptive_card":
            return ImageData(adaptive_card=json.loads(response_obj))
        case _:  # "markdown"
            return ImageData(markdown=response_obj)


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
        size: Image size
        processing_time_ms: Processing time in milliseconds
        enhanced_prompt: Enhanced/refined prompt if available

    Returns:
        ImageResponse with success status
    """
    metadata = ResponseMetadata(
        prompt=prompt,
        enhanced_prompt=enhanced_prompt,
        size=size,
        response_format=response_format,
        processing_time_ms=processing_time_ms,
    )

    logger.debug("Operation successful - time: %d ms", processing_time_ms)

    return ImageResponse(
        status="success",
        data=_build_image_data(response_obj, response_format),
        metadata=metadata,
    )


def _build_error_response(
    prompt: str,
    size: str,
    response_format: str,
    code: str,
    message: str,
    details: str = "",
) -> ImageResponse:
    """Build error response.

    Args:
        prompt: Original prompt
        size: Image size
        response_format: Response format
        code: Error code
        message: Error message
        details: Error details

    Returns:
        ImageResponse with error status
    """
    metadata = ResponseMetadata(
        prompt=prompt,
        size=size,
        response_format=response_format,
    )
    return ImageResponse(
        status="error",
        metadata=metadata,
        error=ErrorDetail(code=code, message=message, details=details),
    )


def get_generator(request: Request) -> ImageGenerator:
    """Dependency to inject generator from app state.

    Args:
        request: FastAPI request object

    Returns:
        OpenAI image generator instance

    Raises:
        HTTPException: If generator not initialized
    """
    generator = getattr(request.app.state, "generators", {}).get(GENERATOR_ID)
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
    generator: Annotated[ImageGenerator, Depends(get_generator)],
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
        "Generating image - format: %s, size: %s",
        request.response_format,
        request.size,
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
        logger.exception("Unexpected error during image generation: %s", e)
        return _build_error_response(
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
    generator: Annotated[ImageGenerator, Depends(get_generator)],
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
        "Editing images - format: %s, size: %s",
        request.response_format,
        request.size,
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
        logger.exception("Unexpected error during image editing: %s", e)
        return _build_error_response(
            request.prompt,
            request.size,
            request.response_format,
            "INTERNAL_ERROR",
            "Internal server error",
            str(e),
        )
