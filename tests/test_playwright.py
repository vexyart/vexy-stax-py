# this_file: tests/test_playwright.py
"""Smoke tests for the playwright engine (SPEC.md §5.3, §8).

Gated by ``@pytest.mark.playwright`` and skipped unless playwright is importable,
a Chromium browser is installed, and the built ``vexy-stax-js`` bundle exists
(this engine drives the JS build in a headless browser). Stills render the airbl
example at the gate size and assert the variance gate so a blank/near-blank render
fails: a real render of the textured deck has high pixel variance and thousands of
distinct colors.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"
DIST = REPO_ROOT / "vexy-stax-js" / "dist" / "vexy-stax.element.js"

# Small render size keeps headless renders fast; matches the hard verification gate.
RENDER_W, RENDER_H = 640, 414

# A blank/near-blank render has tiny variance and few unique colors; a real
# render of the colorful airbl deck clears both thresholds comfortably.
MIN_STD = 30.0
MIN_UNIQUE_COLORS = 500


def _playwright_available() -> bool:
    """True when playwright + an installed Chromium + the JS bundle are present."""
    if importlib.util.find_spec("playwright") is None:
        return False
    if not DIST.exists():
        return False
    try:  # a missing browser binary raises here, not at import.
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _playwright_available(),
    reason="playwright not importable, no Chromium installed, or JS bundle not built",
)


@pytest.fixture
def small_scene():
    """Example scene scaled down to the gate render size."""
    from vexy_stax.scene import load_scene

    scene = load_scene(EXAMPLE)
    scale = RENDER_W / scene.size.width
    scene.size.width = RENDER_W
    scene.size.height = RENDER_H
    scene.camera.gap = scene.camera.gap * scale
    return scene


def _content_stats(path: Path) -> tuple[float, int]:
    """Return (pixel std-dev, unique-color count) for an RGB image."""
    import numpy as np

    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"))
    std = float(arr.std())
    unique = int(len(np.unique(arr.reshape(-1, 3), axis=0)))
    return std, unique


@pytest.mark.playwright
@pytest.mark.parametrize("view", ["compact", "expanded"])
def test_render_still(view: str, small_scene, tmp_path: Path) -> None:
    from vexy_stax.engines.playwright import PlaywrightEngine

    out = tmp_path / f"{view}.png"
    PlaywrightEngine().render_image(small_scene, view, out)  # type: ignore[arg-type]

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


@pytest.mark.playwright
@pytest.mark.slow
def test_render_video(small_scene, tmp_path: Path) -> None:
    from vexy_stax.engines.playwright import PlaywrightEngine

    # Shorten the transition so the opt-in video test stays quick.
    assert small_scene.transition is not None
    small_scene.transition.kind = "expand"
    small_scene.transition.duration = 0.2
    small_scene.transition.wait = 0.0
    small_scene.transition.fps = 10

    out = tmp_path / "morph.mp4"
    PlaywrightEngine().render_video(small_scene, out)
    assert out.exists() and out.stat().st_size > 0
