# this_file: tests/test_image_comparison.py
"""Tests for image comparison utilities."""

import numpy as np
import pytest

from vexy_stax.image_comparison import (
    ComparisonResult,
    compare_images,
    load_image,
)


class TestComparisonResult:
    """Test ComparisonResult dataclass.

    Thresholds are relaxed for cross-renderer comparison:
    - MAE < 35 (was 5) - allows ~14% average pixel difference
    - pixel_match_ratio > 0.35 (was 0.95) - allows 35% match
    """

    def test_passed_when_metrics_good(self):
        """Passes when MAE < 35 and match > 35%."""
        result = ComparisonResult(
            mae=20.0,
            pixel_match_ratio=0.50,
            max_diff=100,
            diff_image=None,
        )
        assert result.passed is True

    def test_failed_when_mae_high(self):
        """Fails when MAE >= 35."""
        result = ComparisonResult(
            mae=40.0,
            pixel_match_ratio=0.50,
            max_diff=150,
            diff_image=None,
        )
        assert result.passed is False

    def test_failed_when_match_low(self):
        """Fails when pixel match < 35%."""
        result = ComparisonResult(
            mae=20.0,
            pixel_match_ratio=0.30,
            max_diff=100,
            diff_image=None,
        )
        assert result.passed is False

    def test_summary_format(self):
        """Summary includes all metrics."""
        result = ComparisonResult(
            mae=3.5,
            pixel_match_ratio=0.96,
            max_diff=25,
            diff_image=None,
        )
        summary = result.summary()
        assert "PASS" in summary
        assert "3.50" in summary
        assert "96" in summary
        assert "25" in summary


class TestCompareImages:
    """Test compare_images function."""

    def test_identical_images_perfect_match(self):
        """Identical images have zero MAE and 100% match."""
        img = np.full((100, 100, 4), 128, dtype=np.uint8)

        result = compare_images(img, img.copy())

        assert result.mae == pytest.approx(0.0)
        assert result.pixel_match_ratio == pytest.approx(1.0)
        assert result.max_diff == 0
        assert result.passed is True

    def test_slightly_different_within_tolerance(self):
        """Small differences within tolerance still pass."""
        img1 = np.full((50, 50, 4), 100, dtype=np.uint8)
        img2 = np.full((50, 50, 4), 105, dtype=np.uint8)  # 5 units off

        result = compare_images(img1, img2, tolerance=10)

        assert result.mae == pytest.approx(5.0)
        assert result.pixel_match_ratio == pytest.approx(1.0)
        assert result.max_diff == 5

    def test_different_images_fail(self):
        """Very different images fail comparison."""
        img1 = np.full((50, 50, 4), 0, dtype=np.uint8)  # Black
        img2 = np.full((50, 50, 4), 255, dtype=np.uint8)  # White

        result = compare_images(img1, img2)

        assert result.mae == pytest.approx(255.0)
        assert result.pixel_match_ratio == pytest.approx(0.0)
        assert result.max_diff == 255
        assert result.passed is False

    def test_dimension_mismatch_raises(self):
        """Raises error when image dimensions don't match."""
        img1 = np.zeros((100, 100, 4), dtype=np.uint8)
        img2 = np.zeros((50, 50, 4), dtype=np.uint8)

        with pytest.raises(ValueError, match="dimensions don't match"):
            compare_images(img1, img2)

    def test_diff_image_generated(self):
        """Diff image is generated when requested."""
        img1 = np.full((10, 10, 4), 100, dtype=np.uint8)
        img2 = np.full((10, 10, 4), 150, dtype=np.uint8)

        result = compare_images(img1, img2, generate_diff=True)

        assert result.diff_image is not None
        assert result.diff_image.shape == (10, 10, 4)
        # Diff should have red channel for differences
        assert np.any(result.diff_image[:, :, 0] > 0)

    def test_diff_image_skipped(self):
        """Diff image not generated when disabled."""
        img = np.full((10, 10, 4), 100, dtype=np.uint8)

        result = compare_images(img, img, generate_diff=False)

        assert result.diff_image is None

    def test_partial_difference(self):
        """Partial differences reflected in metrics."""
        img1 = np.full((100, 100, 4), 100, dtype=np.uint8)
        img2 = img1.copy()
        # Make top half different (50% of pixels)
        img2[:50, :, :] = 200

        result = compare_images(img1, img2, tolerance=10)

        # 50% of pixels should be outside tolerance
        assert result.pixel_match_ratio == pytest.approx(0.5)
        assert result.max_diff == 100


class TestLoadImage:
    """Test load_image function."""

    def test_load_rgba_image(self, tmp_path):
        """Loads RGBA image correctly."""
        import imageio.v3 as iio

        img = np.full((50, 50, 4), [255, 0, 0, 255], dtype=np.uint8)
        path = tmp_path / "test.png"
        iio.imwrite(path, img)

        loaded = load_image(path)

        assert loaded.shape == (50, 50, 4)
        assert loaded.dtype == np.uint8
        np.testing.assert_array_equal(loaded, img)

    def test_load_rgb_converts_to_rgba(self, tmp_path):
        """RGB images get alpha channel added."""
        import imageio.v3 as iio

        img = np.full((50, 50, 3), [0, 255, 0], dtype=np.uint8)
        path = tmp_path / "test.png"
        iio.imwrite(path, img)

        loaded = load_image(path)

        assert loaded.shape == (50, 50, 4)
        # Alpha should be 255
        assert np.all(loaded[:, :, 3] == 255)
