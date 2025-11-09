"""Request and response models for REST API."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from server.backend.models import EditImageInput, GenerationInput

__all__ = [
    "EditImageInput",
    "ErrorDetail",
    "GenerationInput",
    "ImageData",
    "ImageResponse",
    "ResponseMetadata",
]


class ResponseMetadata(BaseModel):
    """Metadata for responses."""

    prompt: str
    model: str
    n: int
    size: str
    quality: str
    user: str
    timestamp: str = Field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    processing_time_ms: int = 0


class ImageData(BaseModel):
    """Image data in response."""

    images: list[str] = Field(default_factory=list, description="Base64 images")
    markdown: str = Field(default="", description="Markdown with embedded images")


class ErrorDetail(BaseModel):
    """Error details in response."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: str = Field(default="", description="Additional details")


class ImageResponse(BaseModel):
    """Unified response model for image endpoints."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "data": {
                    "images": ["base64_encoded_image_data"],
                    "markdown": (
                        "# Generated Images\n![Image](data:image/png;base64,...)"
                    ),
                },
                "metadata": {
                    "prompt": "Example prompt",
                    "model": "gpt-image-1",
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "high",
                    "user": "user123",
                    "timestamp": "2025-11-09T12:00:00.000000",
                    "processing_time_ms": 1234,
                },
                "error": None,
            }
        }
    )

    status: Literal["success", "error"] = "success"
    data: ImageData | None = None
    metadata: ResponseMetadata | None = None
    error: ErrorDetail | None = None
