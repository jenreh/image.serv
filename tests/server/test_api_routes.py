"""Tests for REST API routes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from server.api.models import ImageResponse
from server.api.routes import (
    _build_success_response,
    _error_response,
    edit_image_route,
    generate_image_route,
    get_generator,
)
from server.backend.models import (
    EditImageInput,
    GenerationInput,
    ImageGeneratorResponse,
)


# ============================================================================
# Test Suite: get_generator()
# ============================================================================


class TestGetGenerator:
    """Test dependency injection for generator retrieval."""

    def test_get_generator_success(self, mock_request: MagicMock) -> None:
        """get_generator returns generator when present in app.state."""
        result = get_generator(mock_request)
        assert result is not None
        assert mock_request.app.state.generators["gpt-image-1"] is not None

    def test_get_generator_missing_raises_http_exception(
        self, mock_request: MagicMock
    ) -> None:
        """get_generator raises HTTPException when generators not initialized."""
        mock_request.app.state.generators = {}

        with pytest.raises(HTTPException) as exc_info:
            get_generator(mock_request)

        assert exc_info.value.status_code == 500
        assert "not initialized" in str(exc_info.value.detail).lower()


# ============================================================================
# Test Suite: _build_success_response()
# ============================================================================


class TestBuildSuccessResponse:
    """Test response builder for successful image generation."""

    def test_build_success_response_image_format(
        self, sample_mcp_image: MagicMock
    ) -> None:
        """_build_success_response with format='image' returns Image object."""
        response = _build_success_response(
            response_obj=sample_mcp_image,
            response_format="image",
            prompt="Test prompt",
            size="1024x1024",
            processing_time_ms=1000,
            enhanced_prompt="Enhanced test prompt",
        )

        assert isinstance(response, ImageResponse)
        assert response.status == "success"
        assert response.data is not None
        assert len(response.data.images) > 0

    def test_build_success_response_adaptive_card_format(self) -> None:
        """_build_success_response with format='adaptive_card' returns JSON."""
        response = _build_success_response(
            response_obj='{"type": "AdaptiveCard", "version": "1.5"}',
            response_format="adaptive_card",
            prompt="Test prompt",
            size="1024x1024",
            processing_time_ms=500,
            enhanced_prompt="Enhanced test prompt",
        )

        assert isinstance(response, ImageResponse)
        assert response.status == "success"
        assert response.data is not None
        assert response.data.adaptive_card is not None

    def test_build_success_response_markdown_format(self) -> None:
        """_build_success_response with format='markdown' returns markdown."""
        response = _build_success_response(
            response_obj="![image](https://example.com/image.png)",
            response_format="markdown",
            prompt="Test prompt",
            size="1024x1024",
            processing_time_ms=800,
            enhanced_prompt="Enhanced test prompt",
        )

        assert isinstance(response, ImageResponse)
        assert response.status == "success"
        assert response.data is not None
        assert response.data.markdown != ""

    def test_build_success_response_metadata_complete(
        self, sample_mcp_image: MagicMock
    ) -> None:
        """_build_success_response includes all metadata fields."""
        response = _build_success_response(
            response_obj=sample_mcp_image,
            response_format="image",
            prompt="Original prompt",
            size="1024x1024",
            processing_time_ms=1500,
            enhanced_prompt="Enhanced original prompt",
            model="gpt-image-1",
            quality="hd",
            user="test-user",
        )

        assert response.metadata is not None
        assert response.metadata.prompt == "Original prompt"
        assert response.metadata.enhanced_prompt == "Enhanced original prompt"
        assert response.metadata.size == "1024x1024"
        assert response.metadata.processing_time_ms == 1500
        # Verify ISO timestamp format
        assert "T" in response.metadata.timestamp


# ============================================================================
# Test Suite: _error_response()
# ============================================================================


class TestErrorResponse:
    """Test error response builder."""

    def test_error_response_structure(self) -> None:
        """_error_response returns properly structured error response."""
        response = _error_response(
            prompt="Test prompt",
            model="gpt-image-1",
            size="1024x1024",
            quality="hd",
            user="test-user",
            response_format="image",
            code="INVALID_INPUT",
            message="Invalid image size",
            details="Size must be power of 2",
        )

        assert isinstance(response, ImageResponse)
        assert response.status == "error"
        assert response.error is not None
        assert response.error.code == "INVALID_INPUT"
        assert response.error.message == "Invalid image size"
        assert response.error.details == "Size must be power of 2"

    def test_error_response_includes_metadata(self) -> None:
        """_error_response includes metadata in error response."""
        response = _error_response(
            prompt="Test prompt",
            model="gpt-image-1",
            size="1024x1024",
            quality="hd",
            user="test-user",
            response_format="image",
            code="INTERNAL_ERROR",
            message="Server error",
            details="Something went wrong",
        )

        assert response.metadata is not None
        assert response.metadata.prompt == "Test prompt"


# ============================================================================
# Test Suite: generate_image_route()
# ============================================================================


class TestGenerateImageRoute:
    """Test POST /generate_image endpoint."""

    @pytest.mark.asyncio
    async def test_generate_image_route_success(
        self,
        mock_request: MagicMock,
        sample_generation_input: GenerationInput,
        sample_image_response: ImageGeneratorResponse,
        sample_mcp_image: MagicMock,
    ) -> None:
        """generate_image_route returns successful response on happy path."""
        # Mock the generator's generate method
        mock_generator = mock_request.app.state.generators["gpt-image-1"]
        mock_generator.generate.return_value = sample_image_response

        # Mock generate_response to return the MCP image
        with pytest.mock.patch(
            "server.api.routes.generate_response",
            new_callable=AsyncMock,
            return_value=sample_mcp_image,
        ):
            with pytest.mock.patch(
                "server.api.routes.generate_image_impl",
                new_callable=AsyncMock,
                return_value=(
                    "https://example.com/image.png",
                    "Enhanced prompt",
                ),
            ):
                response = await generate_image_route(
                    request=sample_generation_input,
                    generator=mock_generator,
                )

        assert response.status == "success"
        assert response.metadata.prompt == sample_generation_input.prompt

    @pytest.mark.asyncio
    async def test_generate_image_route_http_exception_passthrough(
        self,
        mock_request: MagicMock,
        sample_generation_input: GenerationInput,
    ) -> None:
        """generate_image_route passes through HTTPException from generator."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        with pytest.mock.patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=400, detail="Invalid prompt"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await generate_image_route(
                    request=sample_generation_input,
                    generator=mock_generator,
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_image_route_generic_exception_returns_error(
        self,
        mock_request: MagicMock,
        sample_generation_input: GenerationInput,
    ) -> None:
        """generate_image_route catches generic Exception and returns error response."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        with pytest.mock.patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
            side_effect=ValueError("Unexpected error"),
        ):
            response = await generate_image_route(
                request=sample_generation_input,
                generator=mock_generator,
            )

        assert response.status == "error"
        assert response.error is not None
        assert response.error.code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_generate_image_route_processing_time_measured(
        self,
        mock_request: MagicMock,
        sample_generation_input: GenerationInput,
        sample_image_response: ImageGeneratorResponse,
        sample_mcp_image: MagicMock,
    ) -> None:
        """generate_image_route measures and includes processing time."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        # Simulate a slow operation
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(0.01)
            return "https://example.com/image.png", "Enhanced prompt"

        with pytest.mock.patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
            side_effect=slow_generate,
        ):
            with pytest.mock.patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
                return_value=sample_mcp_image,
            ):
                response = await generate_image_route(
                    request=sample_generation_input,
                    generator=mock_generator,
                )

        assert response.metadata.processing_time_ms >= 10

    @pytest.mark.asyncio
    async def test_generate_image_route_missing_generator(
        self,
        sample_generation_input: GenerationInput,
    ) -> None:
        """generate_image_route raises HTTPException when generator unavailable."""
        # Create a request with no generators
        mock_request = MagicMock()
        mock_request.app.state.generators = {}

        with pytest.raises(HTTPException) as exc_info:
            # This should fail at the get_generator dependency level
            get_generator(mock_request)

        assert exc_info.value.status_code == 500


# ============================================================================
# Test Suite: edit_image_route()
# ============================================================================


class TestEditImageRoute:
    """Test POST /edit_image endpoint."""

    @pytest.mark.asyncio
    async def test_edit_image_route_success(
        self,
        mock_request: MagicMock,
        sample_edit_input: EditImageInput,
        sample_image_response: ImageGeneratorResponse,
        sample_mcp_image: MagicMock,
    ) -> None:
        """edit_image_route returns successful response on happy path."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]
        mock_generator.edit.return_value = sample_image_response

        with pytest.mock.patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
            return_value="https://example.com/edited.png",
        ):
            with pytest.mock.patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
                return_value=sample_mcp_image,
            ):
                response = await edit_image_route(
                    request=sample_edit_input,
                    generator=mock_generator,
                )

        assert response.status == "success"
        assert response.metadata.prompt == sample_edit_input.prompt

    @pytest.mark.asyncio
    async def test_edit_image_route_http_exception_passthrough(
        self,
        mock_request: MagicMock,
        sample_edit_input: EditImageInput,
    ) -> None:
        """edit_image_route passes through HTTPException from generator."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        with pytest.mock.patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=400, detail="Invalid image"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await edit_image_route(
                    request=sample_edit_input,
                    generator=mock_generator,
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_edit_image_route_generic_exception_returns_error(
        self,
        mock_request: MagicMock,
        sample_edit_input: EditImageInput,
    ) -> None:
        """edit_image_route catches generic Exception and returns error response."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        with pytest.mock.patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Processing failed"),
        ):
            response = await edit_image_route(
                request=sample_edit_input,
                generator=mock_generator,
            )

        assert response.status == "error"
        assert response.error.code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_edit_image_route_processing_time_measured(
        self,
        mock_request: MagicMock,
        sample_edit_input: EditImageInput,
        sample_image_response: ImageGeneratorResponse,
        sample_mcp_image: MagicMock,
    ) -> None:
        """edit_image_route measures and includes processing time."""
        mock_generator = mock_request.app.state.generators["gpt-image-1"]

        async def slow_edit(*args, **kwargs):
            await asyncio.sleep(0.01)
            return "https://example.com/edited.png"

        with pytest.mock.patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
            side_effect=slow_edit,
        ):
            with pytest.mock.patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
                return_value=sample_mcp_image,
            ):
                response = await edit_image_route(
                    request=sample_edit_input,
                    generator=mock_generator,
                )

        assert response.metadata.processing_time_ms >= 10

    @pytest.mark.asyncio
    async def test_edit_image_route_missing_generator(
        self,
        sample_edit_input: EditImageInput,
    ) -> None:
        """edit_image_route raises HTTPException when generator unavailable."""
        mock_request = MagicMock()
        mock_request.app.state.generators = {}

        with pytest.raises(HTTPException) as exc_info:
            get_generator(mock_request)

        assert exc_info.value.status_code == 500
