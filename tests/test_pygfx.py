# this_file: tests/test_pygfx.py
"""Smoke tests for the pygfx engine (SPEC.md §5.3, §8).

Gated by ``@pytest.mark.pygfx`` and skipped unless pygfx is importable (and a GPU
adapter is reachable). Stills render the airbl example at a small size and assert
the variance gate so a blank/near-blank render fails: a real render of the
textured deck has high pixel variance and thousands of distinct colors.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PIL import Image

EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"

# Small render size keeps GPU stills fast; matches the hard verification gate.
RENDER_W, RENDER_H = 640, 414

# A blank/near-blank render has tiny variance and few unique colors; a real
# render of the colorful airbl deck clears both thresholds comfortably.
MIN_STD = 30.0
MIN_UNIQUE_COLORS = 500


def _pygfx_available() -> bool:
    """True when pygfx and a working GPU adapter are reachable."""
    if importlib.util.find_spec("pygfx") is None:
        return False
    try:  # an unreachable/headless adapter raises here, not at import.
        import pygfx as gfx
        from rendercanvas.offscreen import RenderCanvas

        gfx.WgpuRenderer(RenderCanvas(size=(8, 8), pixel_ratio=1))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pygfx_available(),
    reason="pygfx not importable or no GPU adapter available",
)


@pytest.fixture
def small_scene():
    """Example scene scaled down to the gate render size."""
    from vexy_stax.scene import load_scene

    scene = load_scene(EXAMPLE)
    scene.size.width = RENDER_W
    scene.size.height = RENDER_H
    return scene


def _content_stats(path: Path) -> tuple[float, int]:
    """Return (pixel std-dev, unique-color count) for an RGB image."""
    import numpy as np

    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"))
    std = float(arr.std())
    unique = int(len(np.unique(arr.reshape(-1, 3), axis=0)))
    return std, unique


@pytest.mark.pygfx
@pytest.mark.parametrize("view", ["compact", "expanded"])
def test_render_still(view: str, small_scene, tmp_path: Path) -> None:
    from vexy_stax.engines.pygfx import PygfxEngine

    out = tmp_path / f"{view}.png"
    PygfxEngine().render_image(small_scene, view, out)  # type: ignore[arg-type]

    assert out.exists(), f"{view} PNG was not created"
    assert out.stat().st_size > 0, f"{view} PNG is empty"
    with Image.open(out) as im:
        assert im.size == (RENDER_W, RENDER_H), f"{view} PNG has wrong size: {im.size}"

    # Reject blank/near-blank output: the deck must actually be visible.
    std, unique = _content_stats(out)
    assert std > MIN_STD, f"{view} render is near-blank (std={std:.1f} <= {MIN_STD})"
    assert unique > MIN_UNIQUE_COLORS, (
        f"{view} render has too few colors (unique={unique} <= {MIN_UNIQUE_COLORS}); likely blank"
    )


@pytest.mark.pygfx
@pytest.mark.slow
def test_render_video(small_scene, tmp_path: Path) -> None:
    from vexy_stax.engines.pygfx import PygfxEngine

    # Shorten the transition so the opt-in video test stays quick.
    assert small_scene.transition is not None
    small_scene.transition.kind = "expand"
    small_scene.transition.duration = 0.2
    small_scene.transition.wait = 0.0
    small_scene.transition.fps = 10

    out = tmp_path / "morph.mp4"
    PygfxEngine().render_video(small_scene, out)
    assert out.exists() and out.stat().st_size > 0
