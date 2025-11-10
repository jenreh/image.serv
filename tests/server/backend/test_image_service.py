"""Tests for image service helpers."""

from unittest.mock import AsyncMock

import pytest

from server.backend.image_service import generate_image_impl
from server.backend.models import ImageGeneratorResponse, ImageResponseState


@pytest.mark.asyncio
async def test_generate_image_impl_returns_enhanced_prompt() -> None:
    """generate_image_impl should expose enhanced prompt in its result."""
    generator = AsyncMock()
    generator.generate.return_value = ImageGeneratorResponse(
        state=ImageResponseState.SUCCEEDED,
        images=["data:image/png;base64,aW1hZ2Ux"],
        enhanced_prompt="Refined prompt",
    )

    markdown, enhanced_prompt = await generate_image_impl(
        prompt="Original prompt",
        generator=generator,
        model="gpt-image-1",
        n=1,
        size="auto",
        quality="auto",
        user="tester",
    )

    assert enhanced_prompt == "Refined prompt"
    assert "**Prompt:** Original prompt" in markdown
    assert "**Enhanced Prompt:** Refined prompt" in markdown
