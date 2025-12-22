# this_file: src/vexy_stax/image_comparison.py
"""Image comparison utilities for visual regression testing.

Compares pygfx renders to JS reference images using simple metrics.
Uses numpy only (no scikit-image dependency) for minimal footprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class ComparisonResult:
    """Results of comparing two images."""

    mae: float  # Mean Absolute Error (0-255 scale)
    pixel_match_ratio: float  # Fraction of pixels within tolerance (0-1)
    max_diff: int  # Maximum difference in any channel
    diff_image: NDArray[np.uint8] | None  # Difference visualization

    @property
    def passed(self) -> bool:
        """Check if comparison passes default thresholds.

        Cross-renderer comparisons (pygfx vs Three.js) have inherent
        differences due to shader implementations. Thresholds are:
        - MAE < 35: Average pixel difference under ~14% of 255
        - pixel_match_ratio > 0.35: At least 35% pixels within tolerance

        These are relaxed vs pixel-perfect comparison but still catch
        significant regressions like missing layers or wrong geometry.
        """
        return self.mae < 35.0 and self.pixel_match_ratio > 0.35

    def summary(self) -> str:
        """Human-readable summary."""
        status = "PASS" if self.passed else "FAIL"
        return (
            f"{status}: MAE={self.mae:.2f}, "
            f"match={self.pixel_match_ratio:.1%}, "
            f"max_diff={self.max_diff}"
        )


def load_image(path: Path) -> NDArray[np.uint8]:
    """Load image as RGBA numpy array."""
    import imageio.v3 as iio

    img = iio.imread(path)

    # Convert to RGBA if needed
    if img.ndim == 2:
        # Grayscale -> RGBA
        img = np.stack([img, img, img, np.full_like(img, 255)], axis=-1)
    elif img.shape[-1] == 3:
        # RGB -> RGBA
        alpha = np.full((*img.shape[:2], 1), 255, dtype=np.uint8)
        img = np.concatenate([img, alpha], axis=-1)

    return img.astype(np.uint8)


def compare_images(
    test_img: Path | NDArray[np.uint8],
    reference_img: Path | NDArray[np.uint8],
    *,
    tolerance: int = 10,
    generate_diff: bool = True,
) -> ComparisonResult:
    """Compare two images and return quality metrics.

    Parameters
    ----------
    test_img:
        Path to test image or numpy array
    reference_img:
        Path to reference image or numpy array
    tolerance:
        Per-channel tolerance for pixel matching (0-255)
    generate_diff:
        Whether to generate difference visualization

    Returns
    -------
    ComparisonResult with metrics and optional diff image
    """
    # Load images if paths provided
    test = load_image(test_img) if isinstance(test_img, Path) else test_img
    ref = (
        load_image(reference_img) if isinstance(reference_img, Path) else reference_img
    )

    # Validate dimensions match
    if test.shape != ref.shape:
        raise ValueError(f"Image dimensions don't match: {test.shape} vs {ref.shape}")

    # Calculate difference (signed to avoid overflow)
    diff = test.astype(np.int16) - ref.astype(np.int16)
    abs_diff = np.abs(diff)

    # Mean Absolute Error (average across all pixels and channels)
    mae = float(np.mean(abs_diff))

    # Maximum difference in any channel
    max_diff = int(np.max(abs_diff))

    # Pixel match ratio (all channels within tolerance)
    within_tolerance = np.all(abs_diff <= tolerance, axis=-1)
    pixel_match_ratio = float(np.mean(within_tolerance))

    # Generate diff visualization if requested
    diff_image = None
    if generate_diff:
        # Normalize diff to 0-255 range for visualization
        # Red channel shows positive diff, blue shows negative
        diff_viz = np.zeros((*test.shape[:2], 4), dtype=np.uint8)

        # Sum absolute diff across RGB channels
        rgb_diff = np.sum(abs_diff[:, :, :3], axis=-1)

        # Scale to visible range (10x amplification)
        scaled = np.clip(rgb_diff * 10, 0, 255).astype(np.uint8)

        # Red where different, alpha where visible
        diff_viz[:, :, 0] = scaled  # R
        diff_viz[:, :, 3] = np.where(scaled > 0, 255, 0)  # A

        diff_image = diff_viz

    return ComparisonResult(
        mae=mae,
        pixel_match_ratio=pixel_match_ratio,
        max_diff=max_diff,
        diff_image=diff_image,
    )


def save_diff_image(result: ComparisonResult, output_path: Path) -> None:
    """Save the difference visualization to a PNG file."""
    if result.diff_image is None:
        raise ValueError("No diff image available (generate_diff=False?)")

    import imageio.v3 as iio

    output_path.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(output_path, result.diff_image)


__all__ = [
    "ComparisonResult",
    "compare_images",
    "load_image",
    "save_diff_image",
]
