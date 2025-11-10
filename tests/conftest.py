"""Shared pytest fixtures for all tests."""

import base64
import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

from server.backend.generators.openai import OpenAIImageGenerator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    logger.debug("Loading environment variables from %s", {env_path})
    load_dotenv(dotenv_path=str(env_path))
else:
    logger.debug(".env file not found; skipping load.")
    load_dotenv()


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Sample PNG image bytes for testing (1x1 red pixel)."""
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )


@pytest.fixture
def sample_base64_image() -> str:
    """Base64 encoded image data URL."""
    # fmt: off
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    # fmt: on


@pytest.fixture
def temp_image_file(tmp_path: Path, sample_image_bytes: bytes) -> str:
    """Create a temporary image file."""
    image_path = tmp_path / "test_image.png"
    image_path.write_bytes(sample_image_bytes)
    return str(image_path)


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Mock AsyncAzureOpenAI client."""
    client = AsyncMock()

    # Mock image generation response
    mock_gen_response = MagicMock()
    mock_gen_response.data = [MagicMock(b64_json="dGVzdF9pbWFnZV9kYXRh", url=None)]
    client.images.generate.return_value = mock_gen_response

    # Mock image editing response
    mock_edit_response = MagicMock()
    mock_edit_response.data = [MagicMock(b64_json="ZWRpdGVkX2ltYWdlX2RhdGE=", url=None)]
    client.images.edit.return_value = mock_edit_response

    # Mock chat completion for prompt enhancement (async method)
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [
        MagicMock(message=MagicMock(content="Enhanced prompt"))
    ]
    client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

    return client


@pytest.fixture
def mock_google_client() -> MagicMock:
    """Mock Google genai client."""
    client = MagicMock()

    # Mock image generation
    mock_image = MagicMock()
    mock_image.image.image_bytes = b"google_image_data"
    mock_response = MagicMock()
    mock_response.generated_images = [mock_image]
    client.models.generate_images.return_value = mock_response

    # Mock prompt enhancement
    mock_content_response = MagicMock()
    mock_content_response.text = "Enhanced Google prompt"
    client.models.generate_content.return_value = mock_content_response

    return client


@pytest.fixture
def mock_backend_server() -> str:
    """Mock backend server URL."""
    return "http://localhost:8000"


@pytest.fixture
def openai_base_url() -> str:
    """Get OpenAI base URL from environment or use placeholder."""
    url = os.environ.get("OPENAI_BASE_URL", "https://test.openai.azure.com")
    logger.debug("Using OpenAI Base URL: %s", url)
    return url


@pytest.fixture
def openai_api_key() -> str:
    """Get OpenAI API key from environment or use placeholder."""
    key = os.environ.get("OPENAI_API_KEY", "test_openai_key")
    logger.debug("Using OpenAI API Key: %s", key)
    return key


@pytest.fixture
def openai_image_generator(
    openai_api_key: str, openai_base_url: str, backend_server: str
) -> OpenAIImageGenerator:
    """Create OpenAI image generator instance."""
    return OpenAIImageGenerator(
        api_key=openai_api_key,
        base_url=openai_base_url,
        backend_server=backend_server,
    )


@pytest.fixture
def google_api_key() -> str:
    """Get Google API key from environment or use placeholder."""
    return os.environ.get("GOOGLE_API_KEY", "test_google_key")


@pytest.fixture
def backend_server() -> str:
    """Get backend server URL from environment or use placeholder."""
    return os.environ.get("BACKEND_SERVER", "http://localhost:8000")


# ============================================================================
# API Route Fixtures (for REST endpoint testing)
# ============================================================================


@pytest.fixture
def sample_generation_input() -> "GenerationInput":
    """Create a sample GenerationInput for testing."""
    from server.backend.models import GenerationInput

    return GenerationInput(
        prompt="A serene mountain landscape",
        size="1024x1024",
        output_format="png",
        background="opaque",
        response_format="image",
        seed=42,
        enhance_prompt=True,
    )


@pytest.fixture
def sample_edit_input(sample_image_bytes: bytes) -> "EditImageInput":
    """Create a sample EditImageInput for testing."""
    from server.backend.models import EditImageInput

    return EditImageInput(
        image_paths=["https://example.com/test.png"],
        prompt="Apply a filter",
        size="1024x1024",
        output_format="png",
        response_format="image",
    )


@pytest.fixture
def sample_image_response() -> "ImageGeneratorResponse":
    """Create a sample ImageGeneratorResponse from generator."""
    from server.backend.models import ImageGeneratorResponse, ImageResponseState

    return ImageGeneratorResponse(
        state=ImageResponseState.SUCCEEDED,
        images=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="],
        enhanced_prompt="Enhanced: A serene mountain landscape at sunset",
    )


@pytest.fixture
def mock_request(mock_openai_generator_instance: MagicMock) -> MagicMock:
    """Create a mock FastAPI Request with app state containing generators."""
    request = MagicMock()
    request.app.state.generators = {
        "gpt-image-1": mock_openai_generator_instance,
    }
    return request


@pytest.fixture
def mock_openai_generator_instance(mock_openai_client: AsyncMock) -> MagicMock:
    """Create a mock OpenAIImageGenerator instance."""
    from server.backend.generators.openai import OpenAIImageGenerator

    generator = MagicMock(spec=OpenAIImageGenerator)
    generator.id = "gpt-image-1"
    generator.label = "OpenAI Image Generator"
    generator.model = "gpt-image-1"
    generator.generate = AsyncMock()
    generator.edit = AsyncMock()
    return generator


@pytest.fixture
def sample_mcp_image(sample_image_bytes: bytes) -> MagicMock:
    """Create a mock fastmcp.utilities.types.Image object."""
    image = MagicMock()
    image.data = sample_image_bytes
    image.mime_type = "image/png"
    image.url = None
    return image


# Pytest configuration
def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API keys)",
    )
