import logging
import os
import uuid
from abc import ABC
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

import anyio
from pydantic import BaseModel, Field

from server.config import MAX_IMAGES_TO_KEEP

logger = logging.getLogger(__name__)
TMP_PATH: Final[str] = os.environ.get("TMP_PATH", "./images")


class ImageResponseState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ImageInputBase(BaseModel):
    """Base class for image generation and editing inputs."""

    prompt: str = Field(..., description="Text description (max 32000 chars)")

    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = Field(
        default="1024x1024", description="Image dimensions"
    )

    # Output format
    output_format: Literal["png", "jpeg", "webp"] = Field(
        default="jpeg", description="Output image format"
    )

    # Background transparency
    background: Literal["transparent", "opaque", "auto"] = Field(
        default="opaque", description="Background transparency setting"
    )

    # Response format
    response_format: Literal["image", "adaptive_card", "markdown"] = Field(
        default="image",
        description=(
            "Response format: 'image' for MCP Image objects, "
            "'adaptive_card' for Adaptive Card JSON, 'markdown' for markdown string"
        ),
    )


class GenerationInput(ImageInputBase):
    """Input model for image generation (gpt-image-1)."""

    seed: int = Field(
        default=0, description="Random seed for reproducibility (0 = random)"
    )
    enhance_prompt: bool = Field(default=True, description="Auto-enhance prompt")


class EditImageInput(ImageInputBase):
    """Input model for image editing (gpt-image-1)."""

    image_paths: list[str] = Field(
        ...,
        description="List of image URLs, file paths, or base64 data URLs (max 16)",
    )
    mask_path: str | None = Field(
        default=None,
        description=(
            "Optional mask image for inpainting (transparent areas = edit zones)"
        ),
    )


class ImageGeneratorResponse(BaseModel):
    state: ImageResponseState
    images: list[str]
    enhanced_prompt: str | None = None
    error: str = ""


class ImageGenerator(ABC):
    """Base class for image generation."""

    id: str
    model: str
    label: str
    api_key: str
    backend_server: str | None = None

    def __init__(
        self,
        id: str,  # noqa: A002
        label: str,
        model: str,
        api_key: str,
        backend_server: str | None = None,
    ):
        self.id = id
        self.model = model
        self.backend_server = backend_server
        self.label = label
        self.api_key = api_key

    def _format_prompt(self, prompt: str, negative_prompt: str | None = None) -> str:
        """Formats the prompt including an optional negative prompt."""
        if negative_prompt:
            return (
                f"## Image Prompt:\n{prompt}\n\n"
                f"## Negative Prompt (Avoid this in the image):\n{negative_prompt}"
            ).strip()
        return prompt.strip()

    async def _save_image_to_tmp_and_get_url(
        self,
        image_bytes: bytes,
        tmp_file_prefix: str,
        output_format: str,
    ) -> str:
        """
        Saves image bytes to a uniquely named file in the temporary directory
        and returns the full URL to access it.
        """
        if not self.backend_server:
            logger.error(
                "backend_server is not configured for generator %s. "
                "Cannot save image to local temp and construct URL.",
                self.id,
            )
            raise ValueError(
                f"backend_server ist für Generator {self.id} nicht konfiguriert, "
                "um die Bild-URL zu erstellen."
            )

        tmp_dir = Path(TMP_PATH)
        tmp_dir.mkdir(parents=True, exist_ok=True)  # Ensure base temp directory exists

        random_id = uuid.uuid4().hex
        filename = f"{tmp_file_prefix}-{random_id}.{output_format}"
        file_path = tmp_dir / filename

        async with await anyio.open_file(file_path, "wb") as f:
            logger.debug("Writing image to %s", file_path)
            await f.write(image_bytes)

        return f"{self.backend_server}/_upload/{filename}"

    def _aspect_ratio(self, width: int, height: int) -> str:
        """Calculate the aspect ratio based on width and height."""
        if width == height:
            return "1:1"

        if width > height:
            return "4:3"

        return "3:4"

    async def generate(self, input_data: GenerationInput) -> ImageGeneratorResponse:
        """
        Generates images based on the input data.
        Handles common error logging and response for failures.
        """
        try:
            return await self._perform_generation(input_data)
        except Exception as e:
            logger.exception("Error during image generation with %s", self.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, images=[], error=str(e)
            )

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """
        Subclasses must implement this method to perform the actual image generation.
        """
        raise NotImplementedError(
            "Subclasses must implement the _perform_generation method."
        )

    async def edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """
        Edits images based on the input data.
        Handles common error logging and response for failures.
        """
        try:
            return await self._perform_edit(input_data)
        except Exception as e:
            logger.exception("Error during image editing with %s", self.id)
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED, images=[], error=str(e)
            )

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """
        Subclasses must implement this method to perform the actual image editing.
        Raises NotImplementedError if editing is not supported.
        """
        raise NotImplementedError("Subclasses must implement the _perform_edit method.")

    def clean_tmp_path(self, prefix: str) -> Path:
        """Keep only the last MAX_IMAGES_TO_KEEP images with the given prefix.

        Deletes oldest images when the count exceeds the limit.
        """
        tmp_path = Path(TMP_PATH)

        if not tmp_path.exists():
            logger.info("Temporary path %s does not exist. Creating it.", tmp_path)
            tmp_path.mkdir(parents=True, exist_ok=True)
        elif not tmp_path.is_dir():
            logger.error("Temporary path %s is not a directory.", tmp_path)
            raise NotADirectoryError(f"Temporary path {tmp_path} is not a directory.")

        # Get all files matching the prefix, sorted by modification time
        files_with_prefix = sorted(
            (
                f
                for f in tmp_path.iterdir()
                if f.is_file() and f.name.startswith(prefix)
            ),
            key=lambda f: f.stat().st_mtime,  # Oldest first
        )

        # Keep only the last MAX_IMAGES_TO_KEEP images
        if len(files_with_prefix) > MAX_IMAGES_TO_KEEP:
            files_to_delete = files_with_prefix[:-MAX_IMAGES_TO_KEEP]
            for file in files_to_delete:
                logger.debug(
                    "Removing old image: %s (keeping last %d images)",
                    file,
                    MAX_IMAGES_TO_KEEP,
                )
                file.unlink()

        return tmp_path
