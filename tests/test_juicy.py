# this_file: tests/test_juicy.py
"""Tests for vexy_stax.juicy module (ported from vexy-stax2-py)."""

import cv2
import numpy as np

from vexy_stax.juicy import apply_still, compute_corrections


def _create_test_image(path: str, color: tuple, width: int = 100, height: int = 100, alpha: int = 255):
    """Create a solid-color test image with optional alpha."""
    img = np.full((height, width, 4), (*color, alpha), dtype=np.uint8)
    cv2.imwrite(path, img)


def test_compute_corrections_identity(tmp_path):
    """Identical images produce near-identity corrections."""
    img_path = str(tmp_path / "img.png")
    _create_test_image(img_path, (128, 128, 128))

    corrections = compute_corrections(img_path, img_path)
    assert len(corrections) == 3
    for scale, offset in corrections:
        assert abs(scale - 1.0) < 0.1, f"scale {scale} not near 1.0"
        assert abs(offset) < 10.0, f"offset {offset} not near 0.0"


def test_compute_corrections_returns_three_tuples(tmp_path):
    """Returns exactly 3 (scale, offset) tuples."""
    overlay = str(tmp_path / "overlay.png")
    stack = str(tmp_path / "stack.png")
    _create_test_image(overlay, (200, 100, 50))
    _create_test_image(stack, (180, 90, 40))

    corrections = compute_corrections(overlay, stack)
    assert len(corrections) == 3
    for item in corrections:
        assert len(item) == 2


def test_apply_still_preserves_dimensions(tmp_path):
    """Output image has same dimensions as input."""
    img_path = str(tmp_path / "test.png")
    _create_test_image(img_path, (128, 128, 128), width=200, height=150)

    corrections = [(1.1, 5.0), (0.9, -3.0), (1.0, 0.0)]
    # Read as BGR (3 channel) for apply_still
    img = np.full((150, 200, 3), 128, dtype=np.uint8)
    cv2.imwrite(img_path, img)

    apply_still(img_path, corrections)
    result = cv2.imread(img_path)
    assert result.shape == (150, 200, 3)


def test_apply_still_clips_values(tmp_path):
    """Pixel values remain in [0, 255] after correction."""
    img_path = str(tmp_path / "test.png")
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    cv2.imwrite(img_path, img)

    # Aggressive corrections that would overflow
    corrections = [(2.0, 100.0), (2.0, 100.0), (2.0, 100.0)]
    apply_still(img_path, corrections)

    result = cv2.imread(img_path)
    assert result.min() >= 0
    assert result.max() <= 255
