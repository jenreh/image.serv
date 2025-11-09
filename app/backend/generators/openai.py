import base64
import logging
from pathlib import Path
from typing import Final

import anyio
import httpx
from openai import AsyncAzureOpenAI

from app.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageResponseState,
)

logger = logging.getLogger(__name__)

TMP_IMG_FILE: Final[str] = "gpt-image"


class OpenAIImageGenerator(ImageGenerator):
    """Generator for the OpenAI DALL-E API."""

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
        # self.client = AsyncOpenAI(api_key=self.api_key)

        self.client = AsyncAzureOpenAI(
            api_version="2025-04-01-preview",
            azure_endpoint=base_url,
            api_key=api_key,
        )

    async def _enhance_prompt(self, prompt: str) -> str:
        logger.debug("Starting prompt enhancement for: %s", prompt)
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini",
                stream=False,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an image generation assistant specialized in "
                            "optimizing user prompts. Ensure content "
                            "compliance rules are followed. Do not ask followup "
                            "questions, just generate the optimized prompt."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Enhance this prompt for image generation: {prompt}"
                        ),
                    },
                ],
            )
            logger.debug("Prompt enhancement API response received")

            result = response.choices[0].message.content.strip()
            if not result:
                logger.warning(
                    "Prompt enhancement returned empty result, using original"
                )
                result = prompt

            logger.info("Prompt enhanced successfully: %s", result)
            return result
        except Exception as e:
            logger.exception("Prompt enhancement failed: %s", str(e))
            return prompt

    async def _perform_generation(
        self, input_data: GenerationInput
    ) -> ImageGeneratorResponse:
        """Generate images using gpt-image-1 model."""
        logger.info(
            "Starting image generation: model=%s, n=%d, size=%s, quality=%s",
            self.model,
            input_data.n,
            input_data.size,
            input_data.quality,
        )
        logger.debug("Generation input: %s", input_data)

        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        logger.debug("Formatted prompt: %s", prompt)

        if input_data.enhance_prompt:
            logger.info("Prompt enhancement requested")
            prompt = await self._enhance_prompt(prompt)

        logger.debug("Calling OpenAI API with model=%s, prompt=%s", self.model, prompt)

        try:
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=input_data.n,
                size=input_data.size,
                quality=input_data.quality,
                moderation=input_data.moderation,
                output_format=input_data.output_format,
                output_compression=input_data.output_compression,
                background=input_data.background,
            )
            logger.info("OpenAI API response received successfully")
            logger.debug("Response data count: %d", len(response.data))
        except Exception as e:
            logger.exception("OpenAI API call failed")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"API call failed: {e!s}",
            )

        self.clean_tmp_path(TMP_IMG_FILE)
        logger.debug("Cleaned temporary path: %s", TMP_IMG_FILE)

        images = []
        # gpt-image-1 always returns base64
        for idx, img in enumerate(response.data):
            logger.debug("Processing image %d/%d", idx + 1, len(response.data))
            if img.b64_json:
                try:
                    image_bytes = base64.b64decode(img.b64_json)
                    logger.debug(
                        "Decoded base64 image %d: %d bytes",
                        idx + 1,
                        len(image_bytes),
                    )
                    image_url = await self._save_image_to_tmp_and_get_url(
                        image_bytes=image_bytes,
                        tmp_file_prefix=TMP_IMG_FILE,
                        output_format=input_data.output_format,
                    )
                    logger.info(
                        "Image %d saved and URL generated: %s", idx + 1, image_url
                    )
                    images.append(image_url)
                except Exception as e:
                    logger.exception("Failed to process image %d", idx + 1)
                    return ImageGeneratorResponse(
                        state=ImageResponseState.FAILED,
                        images=[],
                        error=f"Failed to process image {idx + 1}: {e!s}",
                    )
            else:
                logger.warning(
                    "Image %d in response has no base64 data, skipping", idx + 1
                )

        if not images:
            logger.error("No images were generated by OpenAI")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error="No images were generated",
            )

        logger.info("Successfully generated %d images", len(images))
        return ImageGeneratorResponse(state=ImageResponseState.SUCCEEDED, images=images)

    async def _load_image(self, path: str) -> bytes:
        """Load image from URL, file path, or base64 data URL."""
        logger.debug("Loading image from: %s", path)

        if path.startswith("data:image"):
            # Decode base64 data URL
            logger.debug("Decoding base64 data URL")
            try:
                base64_data = path.split(",", 1)[1]
                image_bytes = base64.b64decode(base64_data)
                logger.info(
                    "Successfully decoded base64 image: %d bytes", len(image_bytes)
                )
                return image_bytes
            except Exception:
                logger.exception("Failed to decode base64 data URL")
                raise

        if path.startswith(("http://", "https://")):
            # Download from URL
            logger.info("Downloading image from URL: %s", path)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(path)
                    response.raise_for_status()
                    logger.info(
                        "Successfully downloaded image from URL: %d bytes",
                        len(response.content),
                    )
                    return response.content
            except Exception:
                logger.exception("Failed to download image from URL: %s", path)
                raise

        # Read from local file
        logger.info("Reading image from local file: %s", path)
        try:
            async with await anyio.open_file(path, "rb") as f:
                image_bytes = await f.read()
                logger.info(
                    "Successfully read image from file: %d bytes", len(image_bytes)
                )
                return image_bytes
        except Exception:
            logger.exception("Failed to read image from file: %s", path)
            raise

    async def _perform_edit(self, input_data: EditImageInput) -> ImageGeneratorResponse:
        """Edit images using gpt-image-1 model."""
        logger.info(
            "Starting image editing: model=%s, n=%d, size=%s, quality=%s",
            self.model,
            input_data.n,
            input_data.size,
            input_data.quality,
        )
        logger.debug("Edit input: %s", input_data)

        # Load image files (supports up to 16 images)
        logger.info("Loading %d image(s) for editing", len(input_data.image_paths))
        image_files = []
        for idx, img_path in enumerate(input_data.image_paths):
            try:
                logger.debug("Loading image %d: %s", idx + 1, img_path)
                image_bytes = await self._load_image(img_path)
                # Create tuple with filename, data, and mimetype for the API
                filename = (
                    Path(img_path).name if img_path.startswith("/") else "image.png"
                )
                mimetype = f"image/{input_data.output_format}"
                image_tuple = (filename, image_bytes, mimetype)
                image_files.append(image_tuple)
                logger.info("Loaded image %d: %d bytes", idx + 1, len(image_bytes))
            except Exception:
                logger.exception("Failed to load image %d from %s", idx + 1, img_path)
                return ImageGeneratorResponse(
                    state=ImageResponseState.FAILED,
                    images=[],
                    error=f"Failed to load image {idx + 1}",
                )

        # Load mask if provided
        mask_file = None
        if input_data.mask_path:
            try:
                logger.info("Loading mask image: %s", input_data.mask_path)
                mask_file = await self._load_image(input_data.mask_path)
                logger.info("Loaded mask image: %d bytes", len(mask_file))
            except Exception:
                logger.exception("Failed to load mask image: %s", input_data.mask_path)
                return ImageGeneratorResponse(
                    state=ImageResponseState.FAILED,
                    images=[],
                    error="Failed to load mask image",
                )

        prompt = self._format_prompt(input_data.prompt, input_data.negative_prompt)
        logger.debug("Formatted prompt: %s", prompt)

        logger.debug(
            "Calling OpenAI edit API with model=%s, prompt=%s, images=%d",
            self.model,
            prompt,
            len(image_files),
        )

        try:
            # Build API call kwargs dynamically, only including mask if provided
            api_kwargs = {
                "model": self.model,
                "image": image_files,
                "prompt": prompt,
                "n": input_data.n,
                "size": input_data.size,
                "quality": input_data.quality,
                "output_format": input_data.output_format,
                "output_compression": input_data.output_compression,
                "input_fidelity": input_data.input_fidelity,
                "background": input_data.background,
            }
            # Only include mask if it was provided
            if mask_file is not None:
                api_kwargs["mask"] = mask_file

            logger.debug("Calling OpenAI edit API with parameters")
            response = await self.client.images.edit(**api_kwargs)
            logger.info("OpenAI edit API response received successfully")
            logger.debug("Response data count: %d", len(response.data))
        except Exception as e:
            logger.exception("OpenAI edit API call failed")
            return ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error=f"Edit API Error: {e!s}",
            )

        self.clean_tmp_path(TMP_IMG_FILE)
        logger.debug("Cleaned temporary path: %s", TMP_IMG_FILE)

        images = []
        # gpt-image-1 always returns base64
        for idx, img in enumerate(response.data):
            logger.debug("Processing edited image %d/%d", idx + 1, len(response.data))
            if img.b64_json:
                try:
                    image_bytes = base64.b64decode(img.b64_json)
                    logger.debug(
                        "Decoded base64 edited image %d: %d bytes",
                        idx + 1,
                        len(image_bytes),
                    )
                    image_url = await self._save_image_to_tmp_and_get_url(
                        image_bytes=image_bytes,
                        tmp_file_prefix=TMP_IMG_FILE,
                        output_format=input_data.output_format,
                    )
                    logger.info(
                        "Edited image %d saved and URL generated: %s",
                        idx + 1,
                        image_url,
                    )
                    images.append(image_url)
                except Exception:
                    logger.exception("Failed to process edited image %d", idx + 1)
                    return ImageGeneratorResponse(
                        state=ImageResponseState.FAILED,
                        images=[],
                        error=f"Failed to process edited image {idx + 1}",
                    )
            else:
                logger.warning(
                    "Edited image %d in response has no base64 data, skipping", idx + 1
                )

        logger.info("Successfully edited %d images", len(images))
        return ImageGeneratorResponse(state=ImageResponseState.SUCCEEDED, images=images)
