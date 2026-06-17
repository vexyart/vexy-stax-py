# this_file: tests/test_images.py
"""Tests for the image compositing module.

Verifies image dimension loading and flat overlay rendering using the
repository's sample slides.
"""

import os

import pytest
from PIL import Image

from vexy_stax.images import overlay_images, read_images

# Native dimensions / layer count of the airbl-lores slides (see conftest.py).
LAYER_COUNT = 8
LAYER_WIDTH = 1246
LAYER_HEIGHT = 806


def test_read_images_returns_correct_dimensions(image_paths: list[str]):
    """read_images returns correct width/height for each test image."""
    infos = read_images(image_paths)
    assert len(infos) == LAYER_COUNT
    for info in infos:
        assert info["width"] == LAYER_WIDTH
        assert info["height"] == LAYER_HEIGHT


def test_read_images_resolves_absolute_paths(image_paths: list[str]):
    """All returned paths are absolute."""
    infos = read_images(image_paths)
    for info in infos:
        assert os.path.isabs(info["path"])


def test_read_images_missing_file_raises():
    """FileNotFoundError for nonexistent paths."""
    with pytest.raises(FileNotFoundError):
        read_images(["/nonexistent/image.png"])


def test_overlay_images_creates_png(image_paths: list[str], output_dir):
    """overlay_images writes a valid PNG file."""
    infos = read_images(image_paths)
    out = str(output_dir / "overlay.png")
    overlay_images(infos, out)
    assert os.path.isfile(out)
    with Image.open(out) as im:
        assert im.format == "PNG"


def test_overlay_images_canvas_size(image_paths: list[str], output_dir):
    """Canvas dimensions = max(widths) x max(heights)."""
    infos = read_images(image_paths)
    out = str(output_dir / "overlay.png")
    overlay_images(infos, out)
    with Image.open(out) as im:
        assert im.size == (LAYER_WIDTH, LAYER_HEIGHT)


def test_overlay_images_single_image(image_paths: list[str], output_dir):
    """Single image overlay produces the image itself (RGBA)."""
    infos = read_images(image_paths[:1])
    out = str(output_dir / "single.png")
    overlay_images(infos, out)
    assert os.path.isfile(out)
    with Image.open(out) as im:
        assert im.mode == "RGBA"
