# this_file: tests/test_smoke_real_render.py
"""Smoke test for end-to-end pygfx rendering pipeline.

IMPORTANT: This test requires GPU access via wgpu. It will be skipped
in environments without GPU support (e.g., headless CI servers, Docker
without GPU passthrough, or machines without Vulkan/Metal/DirectX).

GPU requirements by platform:
- macOS: Metal support (macOS 10.13+)
- Linux: Vulkan support (driver + vulkan-loader)
- Windows: DirectX 12 or Vulkan support

To skip this test explicitly: pytest -k "not smoke"
"""

from pathlib import Path

import pytest

from vexy_stax.render_pipeline import pygfx_render_png
from vexy_stax.renderer.context import GPUUnavailableError


def test_smoke_render_png_requires_gpu(tmp_path: Path):
    """Validate that PNG rendering pipeline works end-to-end with real GPU.

    This test:
    1. Loads test-img/layer123.json (contains 3 layers)
    2. Renders with real pygfx/wgpu to offscreen canvas
    3. Exports actual PNG file
    4. Validates PNG is readable and has expected dimensions
    """

    # Arrange: locate test scene and output path
    test_scene = Path(__file__).parent.parent / "test-img" / "layer123.json"
    if not test_scene.exists():
        pytest.skip(f"Test scene not found: {test_scene}")

    output_png = tmp_path / "smoke_test.png"

    # Act & Assert: attempt real rendering
    try:
        result = pygfx_render_png(
            scene_json=test_scene,
            output_path=output_png,
            width=400,
            height=300,
            scale=1,
        )
    except GPUUnavailableError as exc:
        pytest.skip(
            f"GPU unavailable, cannot validate real rendering: {exc}\n"
            f"This is expected in headless CI, Docker without GPU, or "
            f"systems without Vulkan/Metal/DirectX support."
        )

    # Validate: PNG file created
    assert output_png.exists(), f"PNG not created at {output_png}"

    # Validate: result metadata matches request
    assert result.path == output_png
    assert result.width == 400
    assert result.height == 300
    assert result.scale == 1

    # Validate: PNG readable by external tool (PIL/imageio)
    from PIL import Image

    with Image.open(output_png) as img:
        assert img.format == "PNG"
        assert img.size == (400, 300)
        assert img.mode in ("RGB", "RGBA")

        # Validate: image has actual content (not blank)
        pixels = list(img.getdata())
        unique_colors = len(set(pixels))
        assert unique_colors > 10, "Rendered image appears blank or too uniform"


def test_smoke_render_png_validates_scale():
    """Verify scale validation happens before GPU initialization."""

    test_scene = Path(__file__).parent.parent / "test-img" / "layer123.json"
    if not test_scene.exists():
        pytest.skip(f"Test scene not found: {test_scene}")

    with pytest.raises(ValueError, match="Scale must be one of"):
        pygfx_render_png(
            scene_json=test_scene,
            output_path="/tmp/invalid.png",
            scale=3,  # invalid
        )


def test_smoke_render_png_handles_missing_scene(tmp_path: Path):
    """Verify loader errors surface clearly."""

    from vexy_stax.loader import LoaderError

    fake_scene = tmp_path / "nonexistent.json"

    with pytest.raises(LoaderError, match="Scene file missing"):
        pygfx_render_png(
            scene_json=fake_scene,
            output_path=tmp_path / "output.png",
        )
