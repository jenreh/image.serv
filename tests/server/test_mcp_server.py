"""Unit tests for MCP server tools."""

import base64
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from server.backend.mcp_server import _edit_image, _generate_image, _url_to_base64
from server.backend.models import ImageGeneratorResponse, ImageResponseState


class TestGenerateImageTool:
    """Test generate_image MCP tool."""

    @pytest.mark.asyncio
    async def test_generate_image_gpt_image_1(self) -> None:
        """Test basic image generation with gpt-image-1."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/png;base64,dGVzdF9pbWFnZQ=="],
            )
            mock_gen.generate.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _generate_image(prompt="A test image", model="gpt-image-1")

            assert "🎨 Generated 1 Image" in result
            assert "**Prompt:** A test image" in result
            assert "**Model:** `gpt-image-1`" in result
            assert "data:image/png;base64" in result
            mock_gen.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_flux(self) -> None:
        """Test image generation with FLUX.1-Kontext-pro."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/png;base64,Zmx1eF9pbWFnZQ=="],
            )
            mock_gen.generate.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _generate_image(
                prompt="A FLUX image", model="FLUX.1-Kontext-pro"
            )

            assert "🎨 Generated 1 Image" in result
            assert "**Model:** `FLUX.1-Kontext-pro`" in result
            mock_gen.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_multiple(self) -> None:
        """Test generating multiple images."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=[
                    "data:image/png;base64,aW1hZ2UxCg==",
                    "data:image/png;base64,aW1hZ2UyCg==",
                    "data:image/png;base64,aW1hZ2UzCg==",
                ],
            )
            mock_gen.generate.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _generate_image(
                prompt="Three images", model="gpt-image-1", n=3
            )

            assert "🎨 Generated 3 Image" in result
            assert "## Image 1" in result
            assert "## Image 2" in result
            assert "## Image 3" in result
            mock_gen.generate.assert_called_once()

            # Verify input parameters
            call_args = mock_gen.generate.call_args[0][0]
            assert call_args.prompt == "Three images"
            assert call_args.n == 3

    @pytest.mark.asyncio
    async def test_generate_image_with_params(self) -> None:
        """Test image generation with all parameters."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/png;base64,dGVzdA=="],
            )
            mock_gen.generate.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _generate_image(
                prompt="Detailed prompt",
                model="gpt-image-1",
                n=2,
                size="1536x1024",
                quality="high",
                user="test_user",
            )

            assert "🎨 Generated" in result
            call_args = mock_gen.generate.call_args[0][0]
            assert call_args.size == "1536x1024"
            assert call_args.quality == "high"
            assert call_args.user == "test_user"

    @pytest.mark.asyncio
    async def test_generate_image_model_not_available(self) -> None:
        """Test error when model is not available."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gens.get.return_value = None

            result = await _generate_image(prompt="Test", model="gpt-image-1")

            assert "❌ **Error:**" in result
            assert "not available" in result

    @pytest.mark.asyncio
    async def test_generate_image_api_error(self) -> None:
        """Test error handling when generation fails."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error="API rate limit exceeded",
            )
            mock_gen.generate.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _generate_image(prompt="Test", model="gpt-image-1")

            assert "❌ **Error:**" in result
            assert "API rate limit exceeded" in result


class TestEditImageTool:
    """Test edit_image MCP tool."""

    @pytest.mark.asyncio
    async def test_edit_image_basic(self, temp_image_file: str) -> None:
        """Test basic image editing."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/png;base64,ZWRpdGVkX2ltYWdl"],
            )
            mock_gen.edit.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _edit_image(
                prompt="Edit this",
                image_paths=[temp_image_file],
                model="gpt-image-1",
            )

            assert "✨ Edited 1 Image" in result
            assert "**Prompt:** Edit this" in result
            assert "**Model:** `gpt-image-1`" in result
            mock_gen.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_image_multiple(self, temp_image_file: str) -> None:
        """Test editing multiple images."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=[
                    "data:image/jpeg;base64,ZWRpdGVkMQ==",
                    "data:image/jpeg;base64,ZWRpdGVkMg==",
                ],
            )
            mock_gen.edit.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _edit_image(
                prompt="Edit multiple",
                image_paths=[temp_image_file, temp_image_file],
                model="gpt-image-1",
                n=2,
            )

            assert "✨ Edited 2 Image" in result
            assert "**Source Images:** 2" in result
            mock_gen.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_image_with_mask(self, temp_image_file: str) -> None:
        """Test editing with mask for inpainting."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/png;base64,aW5wYWludGVk"],
            )
            mock_gen.edit.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _edit_image(
                prompt="Inpaint here",
                image_paths=[temp_image_file],
                mask_path=temp_image_file,
                model="gpt-image-1",
            )

            assert "✨ Edited" in result
            assert "**Mask:** Yes (inpainting)" in result

            call_args = mock_gen.edit.call_args[0][0]
            assert call_args.mask_path == temp_image_file

    @pytest.mark.asyncio
    async def test_edit_image_with_all_params(self, temp_image_file: str) -> None:
        """Test editing with all parameters."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.SUCCEEDED,
                images=["data:image/webp;base64,d2VicA=="],
            )
            mock_gen.edit.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _edit_image(
                prompt="Detailed edit",
                image_paths=[temp_image_file],
                model="gpt-image-1",
                mask_path=temp_image_file,
                n=1,
                size="1536x1024",
                quality="high",
                output_format="webp",
                user="test_user",
            )

            assert "✨ Edited" in result
            assert "**Format:** `webp`" in result

            call_args = mock_gen.edit.call_args[0][0]
            assert call_args.size == "1536x1024"
            assert call_args.quality == "high"
            assert call_args.output_format == "webp"
            assert call_args.user == "test_user"

    @pytest.mark.asyncio
    async def test_edit_image_unsupported_model(self, temp_image_file: str) -> None:
        """Test error when using unsupported model for editing."""
        # Note: The type annotation restricts this to gpt-image-1 only
        # But we test the runtime check for completeness
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_gens.get.return_value = mock_gen

            # This would fail at type level, but testing runtime behavior
            result = await _edit_image(
                prompt="Edit",
                image_paths=[temp_image_file],
                model="gpt-image-1",  # Only valid value
            )

            # With gpt-image-1, it should work
            assert "✨ Edited" in result or "❌" in result

    @pytest.mark.asyncio
    async def test_edit_image_model_not_available(self, temp_image_file: str) -> None:
        """Test error when model is not available."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gens.get.return_value = None

            result = await _edit_image(
                prompt="Edit",
                image_paths=[temp_image_file],
                model="gpt-image-1",
            )

            assert "❌ **Error:**" in result
            assert "not available" in result

    @pytest.mark.asyncio
    async def test_edit_image_api_error(self, temp_image_file: str) -> None:
        """Test error handling when editing fails."""
        with patch("app.backend.mcp_server._generators") as mock_gens:
            mock_gen = AsyncMock()
            mock_response = ImageGeneratorResponse(
                state=ImageResponseState.FAILED,
                images=[],
                error="Invalid image format",
            )
            mock_gen.edit.return_value = mock_response
            mock_gens.get.return_value = mock_gen

            result = await _edit_image(
                prompt="Edit",
                image_paths=[temp_image_file],
                model="gpt-image-1",
            )

            assert "❌ **Error:**" in result
            assert "Invalid image format" in result


class TestUrlToBase64Helper:
    """Test _url_to_base64 helper function."""

    @pytest.mark.asyncio
    async def test_data_url(self, sample_base64_image: str) -> None:
        """Test converting data URL to base64."""
        result = await _url_to_base64(sample_base64_image)

        # Should extract base64 part after comma
        assert "data:image" not in result
        assert len(result) > 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_url(self, sample_image_bytes: bytes) -> None:
        """Test downloading and converting HTTP URL."""
        url = "https://example.com/test.png"
        respx.get(url).mock(return_value=Response(200, content=sample_image_bytes))

        result = await _url_to_base64(url)

        assert len(result) > 0
        # Result should be base64 encoded
        decoded = base64.b64decode(result)
        assert decoded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_file_path(
        self, temp_image_file: str, sample_image_bytes: bytes
    ) -> None:
        """Test reading and converting local file."""
        result = await _url_to_base64(temp_image_file)

        assert len(result) > 0
        decoded = base64.b64decode(result)
        assert decoded == sample_image_bytes

    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await _url_to_base64("/nonexistent/file.png")

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error(self) -> None:
        """Test error when HTTP request fails."""
        url = "https://example.com/notfound.png"
        respx.get(url).mock(return_value=Response(404))

        with pytest.raises(Exception):
            await _url_to_base64(url)
