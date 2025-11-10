"""Tests for backend utility functions."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from server.backend.utils import generate_response, url_to_base64


# ============================================================================
# Test Suite: generate_response()
# ============================================================================


class TestGenerateResponse:
    """Test response generation utility function."""

    @pytest.mark.asyncio
    async def test_generate_response_image_format(
        self, sample_base64_image: str
    ) -> None:
        """generate_response with format='image' returns Image object."""
        result = await generate_response(
            image_url=sample_base64_image,
            response_format="image",
            prompt="Test prompt",
        )

        assert result is not None
        # Image format should have data or be bytes
        assert hasattr(result, "data") or isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_generate_response_adaptive_card_format(
        self, sample_base64_image: str
    ) -> None:
        """generate_response with format='adaptive_card' returns JSON."""
        result = await generate_response(
            image_url=sample_base64_image,
            response_format="adaptive_card",
            prompt="Test prompt",
        )

        assert isinstance(result, str)
        # Should be valid JSON string
        assert "{" in result and "}" in result

    @pytest.mark.asyncio
    async def test_generate_response_markdown_format(self) -> None:
        """generate_response with format='markdown' returns markdown."""
        result = await generate_response(
            image_url="https://example.com/image.png",
            response_format="markdown",
            prompt="Test prompt",
        )

        assert isinstance(result, str)
        assert "![" in result  # Markdown image syntax
        assert "Test prompt" in result

    @pytest.mark.asyncio
    async def test_generate_response_invalid_format_raises_error(
        self, sample_base64_image: str
    ) -> None:
        """generate_response raises ValueError for unknown format."""
        with pytest.raises(ValueError) as exc_info:
            await generate_response(
                image_url=sample_base64_image,
                response_format="invalid_format",  # type: ignore
                prompt="Test prompt",
            )

        assert "format" in str(exc_info.value).lower()


# ============================================================================
# Test Suite: url_to_base64()
# ============================================================================


class TestUrlToBase64:
    """Test URL-to-base64 conversion utility."""

    @pytest.mark.asyncio
    async def test_url_to_base64_http_url(self, sample_image_bytes: bytes) -> None:
        """url_to_base64 downloads and converts HTTP URL."""
        test_url = "https://example.com/image.png"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.content = sample_image_bytes
            mock_response.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await url_to_base64(test_url)

            assert isinstance(result, str)
            # Should be base64 encoded
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_url_to_base64_file_path(
        self, temp_image_file: str, sample_image_bytes: bytes
    ) -> None:
        """url_to_base64 reads local file and converts."""
        result = await url_to_base64(temp_image_file)

        assert isinstance(result, str)
        # Should be base64 encoded
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_url_to_base64_data_url(self, sample_base64_image: str) -> None:
        """url_to_base64 extracts base64 from data URL."""
        result = await url_to_base64(sample_base64_image)

        assert isinstance(result, str)
        # Should return the base64 part without the data:image/png;base64, prefix
        assert "data:image" not in result

    @pytest.mark.asyncio
    async def test_url_to_base64_http_error_propagates(self) -> None:
        """url_to_base64 propagates httpx.HTTPError."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.HTTPError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPError):
                await url_to_base64("https://example.com/missing.png")

    @pytest.mark.asyncio
    async def test_url_to_base64_file_not_found_raises_error(self) -> None:
        """url_to_base64 raises error for missing local file."""
        with pytest.raises((OSError, FileNotFoundError)):
            await url_to_base64("/nonexistent/path/image.png")
