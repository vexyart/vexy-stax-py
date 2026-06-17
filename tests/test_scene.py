# this_file: tests/test_scene.py
"""Tests for the scene model and loader against the airbl example."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vexy_stax.scene import OpacityPerView, Scene, load_scene

# tests/ -> vexy-stax-py/ -> testdata/airbl.scene.json (self-contained fixture)
EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"


def test_example_exists() -> None:
    assert EXAMPLE.is_file(), f"missing fixture: {EXAMPLE}"


def test_loads_eight_slides() -> None:
    scene = load_scene(EXAMPLE)
    assert isinstance(scene, Scene)
    assert scene.version == 1
    assert len(scene.slides) == 8


def test_back_to_front_order() -> None:
    scene = load_scene(EXAMPLE)
    # index 0 farthest (source), last closest (ui)
    assert "020-source" in scene.slides[0].src
    assert "090-ui" in scene.slides[-1].src


def test_opacity_resolution_halftone() -> None:
    scene = load_scene(EXAMPLE)
    halftone = scene.slides[6]  # airbl-080-halftone
    assert "080-halftone" in halftone.src
    assert isinstance(halftone.opacity, OpacityPerView)
    assert halftone.resolved_opacity("compact") == pytest.approx(0.4)
    assert halftone.resolved_opacity("expanded") == pytest.approx(1.0)


def test_scalar_opacity_default() -> None:
    scene = load_scene(EXAMPLE)
    source = scene.slides[0]
    # default scalar 1.0 returns itself for both views
    assert source.resolved_opacity("expanded") == pytest.approx(1.0)
    assert source.resolved_opacity("compact") == pytest.approx(1.0)


def test_src_resolved_absolute() -> None:
    scene = load_scene(EXAMPLE)
    for slide in scene.slides:
        assert Path(slide.src).is_absolute()


def test_extra_forbid_rejects_unknown_key(tmp_path: Path) -> None:
    raw = json.loads(EXAMPLE.read_text())
    raw["unknown_field"] = 123
    bad = tmp_path / "bad.scene.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(ValidationError):
        load_scene(bad)


def test_extra_forbid_rejects_unknown_slide_key(tmp_path: Path) -> None:
    raw = json.loads(EXAMPLE.read_text())
    raw["slides"][0]["bogus"] = True
    bad = tmp_path / "bad2.scene.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(ValidationError):
        load_scene(bad)


def test_data_uri_preserved(tmp_path: Path) -> None:
    raw = json.loads(EXAMPLE.read_text())
    raw["slides"] = [{"src": "data:image/png;base64,AAAA"}]
    f = tmp_path / "data.scene.json"
    f.write_text(json.dumps(raw))
    scene = load_scene(f)
    assert scene.slides[0].src == "data:image/png;base64,AAAA"


def test_transition_parsed() -> None:
    scene = load_scene(EXAMPLE)
    assert scene.transition is not None
    assert scene.transition.kind == "expand_collapse"
    assert scene.transition.fps == 30
