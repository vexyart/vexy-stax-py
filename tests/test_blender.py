# this_file: tests/test_blender.py
"""Smoke tests for the Blender engine (SPEC.md §5.3, §8).

Gated by ``@pytest.mark.blender`` and skipped unless a Blender binary is found.
Stills run in TURBO mode (Eevee, low samples, tiny resolution) so they finish in
seconds. The video test is marked ``slow`` and excluded from the default run.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from vexy_stax.engines.blender import BlenderEngine, _find_blender
from vexy_stax.scene import load_scene

EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"

# Tiny render size keeps turbo stills well under a minute.
TURBO_W, TURBO_H = 480, 310


def _blender_available() -> bool:
    try:
        _find_blender()
        return True
    except FileNotFoundError:
        return False


pytestmark = pytest.mark.skipif(
    not _blender_available(),
    reason="Blender binary not found (PATH / Homebrew / app bundle)",
)


@pytest.fixture
def turbo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force Eevee turbo mode for fast, deterministic test renders."""
    monkeypatch.setenv("VEXY_STAX_TURBO", "1")


@pytest.fixture
def small_scene():
    """Example scene scaled down to a tiny render size."""
    scene = load_scene(EXAMPLE)
    scale = TURBO_W / scene.size.width
    scene.size.width = TURBO_W
    scene.size.height = TURBO_H
    scene.camera.gap = scene.camera.gap * scale
    return scene


# A blank/near-blank render (the old false-pass) has tiny variance and a handful
# of unique colors; a real render of the textured deck has high variance and
# thousands of distinct colors. These thresholds catch the "blank white" failure.
MIN_STD = 28.0
MIN_UNIQUE_COLORS = 500


def _content_stats(path: Path) -> tuple[float, int]:
    """Return (pixel std-dev, unique-color count) for an RGB image."""
    import numpy as np

    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"))
    std = float(arr.std())
    unique = int(len(np.unique(arr.reshape(-1, 3), axis=0)))
    return std, unique


@pytest.mark.blender
@pytest.mark.parametrize("view", ["compact", "expanded"])
def test_render_still(view: str, small_scene, turbo_env, tmp_path: Path) -> None:
    out = tmp_path / f"{view}.png"
    BlenderEngine().render_image(small_scene, view, out)  # type: ignore[arg-type]

    assert out.exists(), f"{view} PNG was not created"
    assert out.stat().st_size > 0, f"{view} PNG is empty"
    with Image.open(out) as im:
        assert im.size == (TURBO_W, TURBO_H), f"{view} PNG has wrong size: {im.size}"

    # Reject blank/near-blank output: the deck must actually be visible.
    std, unique = _content_stats(out)
    assert std > MIN_STD, f"{view} render is near-blank (std={std:.1f} <= {MIN_STD})"
    assert unique > MIN_UNIQUE_COLORS, (
        f"{view} render has too few colors (unique={unique} <= {MIN_UNIQUE_COLORS}); likely blank"
    )


@pytest.mark.blender
@pytest.mark.slow
def test_render_video(small_scene, turbo_env, tmp_path: Path) -> None:
    # Shorten the transition so the opt-in video test stays quick.
    assert small_scene.transition is not None
    small_scene.transition.kind = "expand"
    small_scene.transition.duration = 0.2
    small_scene.transition.wait = 0.0
    small_scene.transition.fps = 10

    out = tmp_path / "morph.mp4"
    BlenderEngine().render_video(small_scene, out)
    assert out.exists() and out.stat().st_size > 0
