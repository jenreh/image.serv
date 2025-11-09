"""Unit tests for data models in app.backend.models."""

import pytest
from pydantic import ValidationError

from server.backend.models import EditImageInput, GenerationInput, ImageInputBase


class TestImageInputBase:
    """Test ImageInputBase model."""

    def test_defaults(self) -> None:
        """Test default values for ImageInputBase."""
        input_data = ImageInputBase(prompt="Test prompt")

        assert input_data.prompt == "Test prompt"
        assert input_data.model == "gpt-image-1"
        assert input_data.size == "auto"
        assert input_data.quality == "auto"
        assert input_data.output_format == "png"
        assert input_data.output_compression == 100
        assert input_data.background == "auto"
        assert input_data.n == 1
        assert input_data.user == "default"

    @pytest.mark.parametrize(
        "size",
        [
            "1024x1024",
            "1536x1024",
            "1024x1536",
            "auto",
        ],
    )
    def test_valid_sizes(self, size: str) -> None:
        """Test all valid size values."""
        input_data = ImageInputBase(prompt="Test", size=size)
        assert input_data.size == size

    @pytest.mark.parametrize("quality", ["low", "medium", "high", "auto"])
    def test_valid_qualities(self, quality: str) -> None:
        """Test all valid quality values."""
        input_data = ImageInputBase(prompt="Test", quality=quality)
        assert input_data.quality == quality

    @pytest.mark.parametrize("output_format", ["png", "jpeg", "webp"])
    def test_valid_output_formats(self, output_format: str) -> None:
        """Test all valid output formats."""
        input_data = ImageInputBase(prompt="Test", output_format=output_format)
        assert input_data.output_format == output_format

    @pytest.mark.parametrize("n", [1, 2, 5, 10])
    def test_valid_n_values(self, n: int) -> None:
        """Test valid n (number of images) values."""
        input_data = ImageInputBase(prompt="Test", n=n)
        assert input_data.n == n

    @pytest.mark.parametrize("n", [0, 11, 100])
    def test_invalid_n_values(self, n: int) -> None:
        """Test invalid n values (outside 1-10 range)."""
        with pytest.raises(ValidationError):
            ImageInputBase(prompt="Test", n=n)

    @pytest.mark.parametrize("output_compression", [0, 50, 100])
    def test_valid_compression_values(self, output_compression: int) -> None:
        """Test valid output_compression values (0-100)."""
        input_data = ImageInputBase(
            prompt="Test", output_compression=output_compression
        )
        assert input_data.output_compression == output_compression

    @pytest.mark.parametrize("output_compression", [-1, 101, 200])
    def test_invalid_compression_values(self, output_compression: int) -> None:
        """Test invalid output_compression values (outside 0-100 range)."""
        with pytest.raises(ValidationError):
            ImageInputBase(prompt="Test", output_compression=output_compression)

    @pytest.mark.parametrize("background", ["transparent", "opaque", "auto"])
    def test_valid_background_values(self, background: str) -> None:
        """Test valid background values."""
        input_data = ImageInputBase(prompt="Test", background=background)
        assert input_data.background == background

    def test_width_property(self) -> None:
        """Test width property extraction."""
        input_data = ImageInputBase(prompt="Test", size="1536x1024")
        assert input_data.width == 1536

    def test_height_property(self) -> None:
        """Test height property extraction."""
        input_data = ImageInputBase(prompt="Test", size="1536x1024")
        assert input_data.height == 1024


class TestGenerationInput:
    """Test GenerationInput model."""

    def test_inherits_from_base(self) -> None:
        """Test that GenerationInput inherits from ImageInputBase."""
        assert issubclass(GenerationInput, ImageInputBase)

    def test_defaults(self) -> None:
        """Test default values for GenerationInput."""
        input_data = GenerationInput(prompt="Test prompt")

        # Base class defaults
        assert input_data.size == "auto"
        assert input_data.quality == "auto"
        assert input_data.model == "gpt-image-1"
        assert input_data.output_format == "png"
        assert input_data.output_compression == 100
        assert input_data.background == "auto"
        assert input_data.n == 1
        assert input_data.user == "default"

        # GenerationInput specific defaults
        assert input_data.prompt == "Test prompt"
        assert input_data.moderation == "auto"
        assert input_data.negative_prompt == ""
        assert input_data.seed == 0
        assert input_data.enhance_prompt is True
        assert input_data.steps == 4

    def test_prompt_required(self) -> None:
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            GenerationInput()

    def test_moderation_values(self) -> None:
        """Test moderation values."""
        input_data = GenerationInput(prompt="Test", moderation="low")
        assert input_data.moderation == "low"

    def test_legacy_parameters(self) -> None:
        """Test legacy parameter support."""
        input_data = GenerationInput(
            prompt="Test",
            negative_prompt="bad quality",
            seed=12345,
            enhance_prompt=False,
            steps=10,
        )

        assert input_data.negative_prompt == "bad quality"
        assert input_data.seed == 12345
        assert input_data.enhance_prompt is False
        assert input_data.steps == 10

    def test_all_parameters_together(self) -> None:
        """Test GenerationInput with all parameters."""
        input_data = GenerationInput(
            prompt="A beautiful landscape",
            model="gpt-image-1",
            size="1536x1024",
            quality="high",
            output_format="webp",
            output_compression=80,
            background="opaque",
            n=3,
            user="test_user",
            moderation="low",
            negative_prompt="blurry",
            seed=42,
            enhance_prompt=True,
            steps=8,
        )

        assert input_data.prompt == "A beautiful landscape"
        assert input_data.model == "gpt-image-1"
        assert input_data.size == "1536x1024"
        assert input_data.quality == "high"
        assert input_data.output_format == "webp"
        assert input_data.output_compression == 80
        assert input_data.background == "opaque"
        assert input_data.n == 3
        assert input_data.user == "test_user"
        assert input_data.moderation == "low"
        assert input_data.negative_prompt == "blurry"
        assert input_data.seed == 42
        assert input_data.enhance_prompt is True
        assert input_data.steps == 8


class TestEditImageInput:
    """Test EditImageInput model."""

    def test_inherits_from_base(self) -> None:
        """Test that EditImageInput inherits from ImageInputBase."""
        assert issubclass(EditImageInput, ImageInputBase)

    def test_defaults(self) -> None:
        """Test default values for EditImageInput."""
        input_data = EditImageInput(prompt="Edit prompt", image_paths=["test.png"])

        # Base class defaults
        assert input_data.size == "auto"
        assert input_data.quality == "auto"
        assert input_data.model == "gpt-image-1"
        assert input_data.output_format == "png"
        assert input_data.output_compression == 100
        assert input_data.background == "auto"
        assert input_data.n == 1
        assert input_data.user == "default"

        # EditImageInput specific defaults
        assert input_data.prompt == "Edit prompt"
        assert input_data.image_paths == ["test.png"]
        assert input_data.mask_path is None
        assert input_data.input_fidelity == "low"
        assert input_data.negative_prompt == ""

    def test_prompt_required(self) -> None:
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            EditImageInput(image_paths=["test.png"])

    def test_image_paths_required(self) -> None:
        """Test that image_paths is required."""
        with pytest.raises(ValidationError):
            EditImageInput(prompt="Test")

    def test_single_image_path(self) -> None:
        """Test with single image path."""
        input_data = EditImageInput(prompt="Edit", image_paths=["image.png"])
        assert len(input_data.image_paths) == 1
        assert input_data.image_paths[0] == "image.png"

    def test_multiple_image_paths(self) -> None:
        """Test with multiple image paths (up to 16)."""
        paths = [f"image{i}.png" for i in range(10)]
        input_data = EditImageInput(prompt="Edit", image_paths=paths)
        assert len(input_data.image_paths) == 10
        assert input_data.image_paths == paths

    def test_mask_path(self) -> None:
        """Test mask_path parameter."""
        input_data = EditImageInput(
            prompt="Edit", image_paths=["image.png"], mask_path="mask.png"
        )
        assert input_data.mask_path == "mask.png"

    @pytest.mark.parametrize("fidelity", ["low", "high"])
    def test_valid_input_fidelity(self, fidelity: str) -> None:
        """Test valid input_fidelity values."""
        input_data = EditImageInput(
            prompt="Edit", image_paths=["image.png"], input_fidelity=fidelity
        )
        assert input_data.input_fidelity == fidelity

    def test_all_parameters_together(self) -> None:
        """Test EditImageInput with all parameters."""
        input_data = EditImageInput(
            prompt="Edit this image",
            image_paths=["image1.png", "image2.png"],
            mask_path="mask.png",
            input_fidelity="high",
            model="gpt-image-1",
            size="1536x1024",
            quality="high",
            output_format="jpeg",
            output_compression=90,
            background="opaque",
            n=2,
            user="test_user",
            negative_prompt="blurry",
        )

        assert input_data.prompt == "Edit this image"
        assert input_data.image_paths == ["image1.png", "image2.png"]
        assert input_data.mask_path == "mask.png"
        assert input_data.input_fidelity == "high"
        assert input_data.model == "gpt-image-1"
        assert input_data.size == "1536x1024"
        assert input_data.quality == "high"
        assert input_data.output_format == "jpeg"
        assert input_data.output_compression == 90
        assert input_data.background == "opaque"
        assert input_data.n == 2
        assert input_data.user == "test_user"
        assert input_data.negative_prompt == "blurry"
