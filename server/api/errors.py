"""REST API error handling and custom exceptions."""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ImageServiceError(Exception):
    """Base exception for image service errors."""

    def __init__(self, message: str, error_code: str = "SERVICE_ERROR") -> None:
        """Initialize error.

        Args:
            message: Error message
            error_code: Error code identifier
        """
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class GenerationError(ImageServiceError):
    """Generation or editing failed."""

    def __init__(self, message: str) -> None:
        """Initialize generation error."""
        super().__init__(message, error_code="GENERATION_FAILED")


class GeneratorError(ImageServiceError):
    """Generator infrastructure error."""

    def __init__(self, message: str) -> None:
        """Initialize generator error."""
        super().__init__(message, error_code="GENERATOR_ERROR")


class InvalidInputError(ImageServiceError):
    """Invalid input provided."""

    def __init__(self, message: str) -> None:
        """Initialize input error."""
        super().__init__(message, error_code="INVALID_INPUT")


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(ImageServiceError)
    async def image_service_error_handler(
        _request: Request, exc: ImageServiceError
    ) -> JSONResponse:
        """Handle ImageServiceError exceptions.

        Args:
            _request: HTTP request object (unused)
            exc: Exception instance

        Returns:
            JSON response with error details
        """
        logger.warning("Image service error [%s]: %s", exc.error_code, exc.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "data": None,
                "metadata": {
                    "timestamp": datetime.now(tz=timezone.utc).isoformat()  # noqa: UP017
                },
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": "",
                },
            },
        )

    @app.exception_handler(GeneratorError)
    async def generator_error_handler(
        _request: Request, exc: GeneratorError
    ) -> JSONResponse:
        """Handle GeneratorError exceptions.

        Args:
            _request: HTTP request object (unused)
            exc: Exception instance

        Returns:
            JSON response with error details
        """
        logger.error("Generator error: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "data": None,
                "metadata": {
                    "timestamp": datetime.now(tz=timezone.utc).isoformat()  # noqa: UP017
                },
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": "Internal server error",
                },
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions.

        Args:
            _request: HTTP request object (unused)
            exc: Exception instance

        Returns:
            JSON response with error details
        """
        logger.exception("Unexpected error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "data": None,
                "metadata": {
                    "timestamp": datetime.now(tz=timezone.utc).isoformat()  # noqa: UP017
                },
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": str(exc),
                },
            },
        )
