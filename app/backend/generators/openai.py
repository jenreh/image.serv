import logging
from typing import Final

from openai import AsyncAzureOpenAI

from app.backend.generators.image_processor import ImageProcessor
from app.backend.generators.prompt_enhancer import PromptEnhancer
from app.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

# API Configuration
TMP_IMG_FILE: Final[str] = "gpt-image"
API_VERSION: Final[str] = "2025-04-01-preview"


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API.

    Uses composition pattern with specialized helper classes for:
    - Image loading (ImageLoader)
    - Prompt enhancement (PromptEnhancer)
    - Image processing (ImageProcessor)
    """

    def __init__(
        self,
        api_key: str,
        id: str = "gpt-image-1",  # noqa: A002
        label: str = "OpenAI GPT-Image-1",
        model: str = "gpt-image-1",
        backend_server: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            model=model,
            api_key=api_key,
            backend_server=backend_server,
        )
        self.client = AsyncAzureOpenAI(
            api_version=API_VERSION,
            azure_endpoint=base_url,
            api_key=api_key,
        )
        # Initialize helper services
        self.prompt_enhancer = PromptEnhancer(self.client)
        self.image_processor = ImageProcessor(self)

    async def _enhance_prompt(self, prompt: str) -> str:
        """Delegate to prompt enhancer (backward compatibility)."""
        return await self.prompt_enhancer.enhance(prompt)

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """Generate images using gpt-image-1 model."""
        logger.debug(
            "Starting image generation: model=%s, size=%s",
            self.model,
            input_data.size,
        )

        # Prepare prompt
        prompt = self._format_prompt(input_data.prompt, "")
        if input_data.enhance_prompt:
            logger.debug("Prompt enhancement requested")
            prompt = await self.prompt_enhancer.enhance(prompt)

        # Call API
        try:
            logger.debug("Calling OpenAI API")
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=input_data.size,
                output_format=input_data.output_format,
                background=input_data.background,
            )
        except Exception as e:
            logger.exception("OpenAI API call failed")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"API call failed: {e!s}",
            )

        # Process response
        self.clean_tmp_path(TMP_IMG_FILE)
        try:
            images = await self.image_processor.save_and_return_images(
                response.data, input_data.output_format
            )
            logger.info("Successfully generated %d images", len(images))
            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED, images=images
            )
        except Exception as e:
            logger.exception("Failed to process generated images")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"Failed to process images: {e!s}",
            )

    async def _load_image(self, path: str) -> bytes:
        """Load image from URL, file path, or base64 data URL."""
        return await self.image_processor.load_image(path)

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """Edit images using gpt-image-1 model."""
        logger.debug(
            "Starting image editing: model=%s, size=%s",
            self.model,
            input_data.size,
        )

        # Load and prepare images
        try:
            image_files = await self.image_processor.prepare_images_for_editing(
                input_data.image_paths, input_data.output_format
            )
        except Exception as e:
            logger.exception("Failed to prepare images for editing")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"Failed to prepare images: {e!s}",
            )

        # Load mask if provided
        mask_file = None
        if input_data.mask_path:
            try:
                mask_file = await self.image_processor.load_image(input_data.mask_path)
                logger.debug("Loaded mask image: %d bytes", len(mask_file))
            except Exception:
                logger.exception("Failed to load mask image")
                return ImageGeneratorResponse(
                    state=ImageResponseState.FAILED,
                    images=[],
                    error="Failed to load mask image",
                )

        # Prepare prompt
        prompt = self._format_prompt(input_data.prompt, "")

        # Call edit API
        try:
            logger.debug("Calling OpenAI edit API")
            api_kwargs = {
                "model": self.model,
                "image": image_files,
                "prompt": prompt,
                "size": input_data.size,
                "output_format": input_data.output_format,
                "background": input_data.background,
            }
            if mask_file is not None:
                api_kwargs["mask"] = mask_file

            response = await self.client.images.edit(**api_kwargs)
        except Exception as e:
            logger.exception("OpenAI edit API call failed")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"Edit API Error: {e!s}",
            )

        # Process response
        self.clean_tmp_path(TMP_IMG_FILE)
        try:
            images = await self.image_processor.save_and_return_images(
                response.data, input_data.output_format
            )
            logger.debug("Successfully edited %d images", len(images))
            return ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED, images=images
            )
        except Exception:
            logger.exception("Failed to process edited images")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error="Failed to process edited images",
            )
