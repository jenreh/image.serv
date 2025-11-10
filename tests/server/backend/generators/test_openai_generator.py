"""Unit tests for OpenAI image generator."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from httpx import Response

from server.backend.generators.openai import OpenAIImageGenerator
from server.backend.models import EditImageInput, GenerationInput
from server.backend.prompt_enhancer import PromptEnhancer


class TestOpenAIImageGeneratorInit:
    """Test OpenAIImageGenerator initialization."""

    def test_init_with_all_params(
        self, openai_api_key: str, openai_base_url: str
    ) -> None:
        """Test initialization with all parameters."""
        generator = OpenAIImageGenerator(
            api_key=openai_api_key,
            base_url=openai_base_url,
            id="test-id",
            label="Test Label",
            model="gpt-image-1",
            backend_server="http://localhost:8000",
        )

        assert generator.id == "test-id"
        assert generator.label == "Test Label"
        assert generator.model == "gpt-image-1"
        assert generator.api_key == openai_api_key
        assert generator.backend_server == "http://localhost:8000"
        assert generator.client is not None

    def test_init_minimal_params(
        self, openai_api_key: str, openai_base_url: str
    ) -> None:
        """Test initialization with minimal parameters."""
        generator = OpenAIImageGenerator(
            api_key=openai_api_key, base_url=openai_base_url
        )

        assert generator.id == "gpt-image-1"
        assert generator.model == "gpt-image-1"
        assert generator.api_key == openai_api_key


class TestOpenAIImageGeneratorGenerate:
    """Test image generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test basic image generation."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = GenerationInput(prompt="Test prompt")
        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert len(response.images) >= 1
        mock_openai_client.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_all_params(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test image generation with all parameters."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = GenerationInput(
            prompt="Detailed prompt",
            size="1024x1024",
            quality="high",
            output_format="webp",
            seed=42,
            n=2,
            output_compression=80,
            enhance_prompt=False,
            moderation="auto",
        )

        # Mock response with 2 images
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="aW1hZ2UxX2RhdGE=", url=None),
            MagicMock(b64_json="aW1hZ2UyX2RhdGE=", url=None),
        ]
        mock_openai_client.images.generate.return_value = mock_response

        response = await generator.generate(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 2
        # Images are saved to backend server, so check for URL format
        assert response.images[0].startswith("http://localhost:8000")
        assert response.images[1].startswith("http://localhost:8000")

        # Verify call arguments
        call_kwargs = mock_openai_client.images.generate.call_args.kwargs
        assert call_kwargs["model"] == "gpt-image-1"
        assert call_kwargs["prompt"] == "Detailed prompt"
        assert call_kwargs["size"] == "1024x1024"
        assert call_kwargs["quality"] == "high"
        assert call_kwargs["output_format"] == "webp"
        assert call_kwargs["n"] == 2

    @pytest.mark.asyncio
    async def test_generate_with_prompt_enhancement(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test image generation with prompt enhancement."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client
        # Need to reinitialize prompt_enhancer with the mock client
        generator.prompt_enhancer = PromptEnhancer(mock_openai_client)

        input_data = GenerationInput(prompt="Simple prompt", enhance_prompt=True)
        response = await generator.generate(input_data)

        # Verify chat completion was called for enhancement
        mock_openai_client.chat.completions.create.assert_called_once()

        # Verify images were generated with enhanced prompt
        call_kwargs = mock_openai_client.images.generate.call_args.kwargs
        assert call_kwargs["prompt"] == "Enhanced prompt"

        assert response.enhanced_prompt == "Enhanced prompt"
        assert len(response.images) == 1


class TestOpenAIImageGeneratorEdit:
    """Test image editing functionality."""

    @pytest.mark.asyncio
    async def test_edit_basic(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test basic image editing."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = EditImageInput(prompt="Edit prompt", image_paths=[temp_image_file])
        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 1
        assert response.images[0].startswith("http://localhost:8000")
        mock_openai_client.images.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_multiple_images(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with multiple images."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = EditImageInput(
            prompt="Edit prompt", image_paths=[temp_image_file, temp_image_file]
        )

        # Mock response with 2 edited images
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(b64_json="ZWRpdGVkMQ==", url=None),
            MagicMock(b64_json="ZWRpdGVkMg==", url=None),
        ]
        mock_openai_client.images.edit.return_value = mock_response

        response = await generator.edit(input_data)

        assert response.state == "succeeded"
        assert len(response.images) == 2
        assert response.images[0].startswith("http://localhost:8000")
        assert response.images[1].startswith("http://localhost:8000")

    @pytest.mark.asyncio
    async def test_edit_with_mask(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with mask."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = EditImageInput(
            prompt="Edit prompt",
            image_paths=[temp_image_file],
            mask_path=temp_image_file,
        )
        response = await generator.edit(input_data)

        assert len(response.images) == 1
        call_kwargs = mock_openai_client.images.edit.call_args.kwargs
        assert "mask" in call_kwargs

    @pytest.mark.asyncio
    async def test_edit_with_all_params(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test editing with all parameters."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        input_data = EditImageInput(
            prompt="Detailed edit",
            image_paths=[temp_image_file],
            mask_path=temp_image_file,
            input_fidelity="high",
            size="1024x1024",
            quality="high",
            output_format="jpeg",
            seed=123,
            n=1,
            output_compression=90,
        )
        response = await generator.edit(input_data)

        assert len(response.images) == 1

        # Verify call arguments
        call_kwargs = mock_openai_client.images.edit.call_args.kwargs
        assert call_kwargs["model"] == "gpt-image-1"
        assert call_kwargs["prompt"] == "Detailed edit"
        assert call_kwargs["size"] == "1024x1024"
        assert call_kwargs["quality"] == "high"
        assert call_kwargs["output_format"] == "jpeg"
        assert call_kwargs["n"] == 1
        assert call_kwargs["output_compression"] == 90
        assert call_kwargs["input_fidelity"] == "high"


class TestOpenAIImageGeneratorLoadImage:
    """Test image loading functionality."""

    @pytest.mark.asyncio
    async def test_load_image_from_file(
        self, temp_image_file: str, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from file path."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        loaded = await generator._load_image(temp_image_file)  # noqa: SLF001

        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    @respx.mock
    async def test_load_image_from_url(
        self, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from URL."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        url = "https://example.com/image.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        loaded = await generator._load_image(url)  # noqa: SLF001
        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_from_base64(
        self, sample_base64_image: str, sample_image_bytes: bytes, openai_base_url: str
    ) -> None:
        """Test loading image from base64 data URL."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        loaded = await generator._load_image(sample_base64_image)  # noqa: SLF001

        assert loaded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_file_not_found(self, openai_base_url: str) -> None:
        """Test loading non-existent file raises error."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        with pytest.raises(FileNotFoundError):
            await generator._load_image("/nonexistent/file.png")  # noqa: SLF001

    @pytest.mark.asyncio
    @respx.mock
    async def test_load_image_url_error(self, openai_base_url: str) -> None:
        """Test loading from URL with HTTP error."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )

        url = "https://example.com/notfound.png"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            await generator._load_image(url)  # noqa: SLF001


class TestOpenAIImageGeneratorErrorHandling:
    """Test error handling in OpenAI generator."""

    @pytest.mark.asyncio
    async def test_generate_api_error(
        self, mock_openai_client: AsyncMock, openai_base_url: str
    ) -> None:
        """Test handling of API errors during generation."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        mock_openai_client.images.generate.side_effect = Exception("API Error")

        input_data = GenerationInput(prompt="Test")

        response = await generator.generate(input_data)

        assert response.state == "failed"
        assert "API Error" in response.error

    @pytest.mark.asyncio
    async def test_edit_api_error(
        self, mock_openai_client: AsyncMock, temp_image_file: str, openai_base_url: str
    ) -> None:
        """Test handling of API errors during editing."""
        generator = OpenAIImageGenerator(
            api_key="test_key",
            base_url=openai_base_url,
            backend_server="http://localhost:8000",
        )
        generator.client = mock_openai_client

        mock_openai_client.images.edit.side_effect = Exception("Edit API Error")

        input_data = EditImageInput(prompt="Edit", image_paths=[temp_image_file])

        response = await generator.edit(input_data)

        assert response.state == "failed"
        assert "Edit API Error" in response.error
