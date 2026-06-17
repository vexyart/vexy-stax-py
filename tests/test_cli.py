# this_file: tests/test_cli.py
"""Tests for the vexy-stax CLI commands, focusing on dir2scene."""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_stax.cli import Stax
from vexy_stax.scene import load_scene

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTDATA_DIR = PROJECT_ROOT / "testdata" / "airbl-lores"


def test_dir2scene_generates_valid_scene(tmp_path: Path) -> None:
    out_json = tmp_path / "scene.json"
    stax = Stax()
    stax.dir2scene(directory=str(TESTDATA_DIR), out=str(out_json))

    assert out_json.is_file()

    # Load and validate the scene using the package's loader
    scene = load_scene(out_json)
    assert scene.version == 1
    assert len(scene.slides) == 8

    # Width and height should match the airbl-lores images (1246x806)
    assert scene.size.width == 1246
    assert scene.size.height == 806

    # Verify that the slide paths are relative to the output JSON directory
    # (Since airbl-lores slides are in testdata/airbl-lores and JSON is in tmp_path)
    # The relative paths will be calculated correctly
    for slide in scene.slides:
        assert Path(slide.src).is_absolute()
        assert "airbl-lores" in slide.src


def test_dir2scene_natural_sorting_and_reverse(tmp_path: Path) -> None:
    # Create a dummy folder with numbered images
    dummy_dir = tmp_path / "images"
    dummy_dir.mkdir()

    # Create empty images
    from PIL import Image

    for idx in [10, 2, 1]:
        img = Image.new("RGBA", (100, 100))
        img.save(dummy_dir / f"layer_{idx}.png")

    out_json = tmp_path / "scene.json"
    stax = Stax()

    # Standard natural sort (ascending)
    stax.dir2scene(directory=str(dummy_dir), out=str(out_json))
    scene = load_scene(out_json)
    assert len(scene.slides) == 3
    # Relpaths resolved as absolute paths inside load_scene:
    assert scene.slides[0].src.endswith("layer_1.png")
    assert scene.slides[1].src.endswith("layer_2.png")
    assert scene.slides[2].src.endswith("layer_10.png")

    # Reversed sort (descending)
    stax.dir2scene(directory=str(dummy_dir), out=str(out_json), reverse=True)
    scene = load_scene(out_json)
    assert scene.slides[0].src.endswith("layer_10.png")
    assert scene.slides[1].src.endswith("layer_2.png")
    assert scene.slides[2].src.endswith("layer_1.png")


def test_dir2scene_custom_parameters(tmp_path: Path) -> None:
    out_json = tmp_path / "custom_scene.json"
    stax = Stax()

    stax.dir2scene(
        directory=str(TESTDATA_DIR),
        out=str(out_json),
        view="compact",
        width=500,
        height=400,
        gap=100.0,
        distance="80%",
        angle=45.0,
        elevation=15.0,
        fov=50.0,
        background="#000000",
        floor_color="#111111",
        floor_opacity=0.8,
        floor_reflectivity=0.2,
        transition_kind="expand",
        transition_duration=4.5,
        transition_wait=2.0,
        transition_fps=60,
        transition_easing="easeOutCubic",
        juicy=True,
    )

    scene = load_scene(out_json)
    assert scene.view == "compact"
    assert scene.size.width == 500
    assert scene.size.height == 400
    assert scene.camera.gap == 100.0
    assert scene.camera.distance == "80%"
    assert scene.camera.angle == 45.0
    assert scene.camera.elevation == 15.0
    assert scene.camera.fov == 50.0
    assert scene.background == "#000000"
    assert scene.floor.color == "#111111"
    assert scene.floor.opacity == 0.8
    assert scene.floor.reflectivity == 0.2
    assert scene.juicy is True

    assert scene.transition is not None
    assert scene.transition.kind == "expand"
    assert scene.transition.duration == 4.5
    assert scene.transition.wait == 2.0
    assert scene.transition.fps == 60
    assert scene.transition.easing == "easeOutCubic"


def test_dir2scene_smart_captions(tmp_path: Path) -> None:
    out_json = tmp_path / "scene.json"
    stax = Stax()
    stax.dir2scene(directory=str(TESTDATA_DIR), out=str(out_json), captions=True)

    scene = load_scene(out_json)
    # The airbl files have prefix "airbl-0" (or similar),
    # resulting in clean capitalized title-case captions like "Source", "Pink", "UI".
    assert scene.slides[0].caption is not None
    assert scene.slides[0].caption.text == "Source"
    assert scene.slides[-1].caption is not None
    assert scene.slides[-1].caption.text == "Ui"


def test_dir2scene_errors(tmp_path: Path) -> None:
    stax = Stax()

    # Non-existent directory
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        stax.dir2scene(directory=str(tmp_path / "nonexistent"))

    # Empty directory (no images)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="No images found"):
        stax.dir2scene(directory=str(empty_dir))
