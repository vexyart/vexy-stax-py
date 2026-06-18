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
    # index 0 farthest (source image), last closest (ui)
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
    assert scene.transition.fps == 20


def test_floor_smoked_glass_defaults() -> None:
    """Issue 303 §1: the floor defaults to ~4% smoked glass (just so visible)."""
    scene = Scene.model_validate({"version": 1, "slides": [{"src": "a.png"}]})
    assert scene.floor.opacity == pytest.approx(0.04)
    assert scene.floor.color == "#1a1a1a"
    assert scene.floor.reflectivity == pytest.approx(0.5)


def test_edge_off_by_default_color_f2f2f2() -> None:
    """Issue 326: plate + caption borders are OFF by default (width 0); color stays #f2f2f2."""
    scene = Scene.model_validate({"version": 1, "slides": [{"src": "a.png"}]})
    assert scene.edge.width == pytest.approx(0.0)  # issue 326: no border by default
    assert scene.edge.color == "#f2f2f2"  # issue 324: default color when a border IS enabled


def test_caption_color_overrides_default_to_edge() -> None:
    """Issue 324: caption fill/border colors are separately overridable, else == edge.color."""
    import vexy_stax.geometry as g

    # Defaults: both caption fill + border fall back to the (default) edge color.
    s = Scene.model_validate({"version": 1, "slides": [{"src": "a.png"}]})
    assert g.caption_fill_color(s) == "#f2f2f2"
    assert g.caption_border_color(s) == "#f2f2f2"
    # Overridable independently via caption_defaults; text color stays separate.
    s2 = Scene.model_validate(
        {
            "version": 1,
            "edge": {"color": "#111111"},
            "caption_defaults": {"color": "#abcdef", "fill_color": "#ff0000", "border_color": "#00ff00"},
            "slides": [{"src": "a.png"}],
        }
    )
    assert g.caption_fill_color(s2) == "#ff0000"
    assert g.caption_border_color(s2) == "#00ff00"
    assert s2.caption_defaults is not None and s2.caption_defaults.color == "#abcdef"
    # Only fill overridden → border still falls back to edge.color.
    s3 = Scene.model_validate(
        {
            "version": 1,
            "edge": {"color": "#222"},
            "caption_defaults": {"fill_color": "#abc"},
            "slides": [{"src": "a.png"}],
        }
    )
    assert g.caption_fill_color(s3) == "#abc"
    assert g.caption_border_color(s3) == "#222"


def test_edge_customizable_and_strict() -> None:
    raw = {"version": 1, "edge": {"width": 0.01, "color": "#ff0000"}, "slides": [{"src": "a.png"}]}
    scene = Scene.model_validate(raw)
    assert scene.edge.width == pytest.approx(0.01)
    assert scene.edge.color == "#ff0000"
    with pytest.raises(ValidationError):  # extra="forbid"
        Scene.model_validate({"version": 1, "edge": {"thickness": 1}, "slides": [{"src": "a.png"}]})


def test_captions_toggle_defaults_true_and_parses() -> None:
    """Issue 332: global `captions` defaults to true and parses an explicit bool."""
    default = Scene.model_validate({"version": 1, "slides": [{"src": "a.png"}]})
    assert default.captions is True  # default preserves prior captioned behavior
    off = Scene.model_validate({"version": 1, "captions": False, "slides": [{"src": "a.png"}]})
    assert off.captions is False
    on = Scene.model_validate({"version": 1, "captions": True, "slides": [{"src": "a.png"}]})
    assert on.captions is True
    # A non-coercible captions value fails loud at the boundary (like the other bool fields).
    with pytest.raises(ValidationError):
        Scene.model_validate({"version": 1, "captions": [1, 2], "slides": [{"src": "a.png"}]})


def test_video_section_defaults() -> None:
    """Issue 335 §3: the video section is always present with behavior-preserving defaults."""
    scene = Scene.model_validate({"version": 1, "slides": [{"src": "a.png"}]})
    assert scene.video.width is None  # null ⇒ fall back to size
    assert scene.video.height is None
    assert scene.video.fps is None  # null ⇒ transition.fps (else 30)
    assert scene.video.frames is None  # null ⇒ derive from transition.duration
    assert scene.video.first_hold == 10  # held first/last stills default-on
    assert scene.video.last_hold == 10


def test_video_section_parses_and_is_strict() -> None:
    """Issue 335 §3: explicit video params parse; unknown keys fail loud (extra='forbid')."""
    raw = {
        "version": 1,
        "video": {"width": 800, "height": 600, "fps": 24, "frames": 50, "first_hold": 3, "last_hold": 7},
        "slides": [{"src": "a.png"}],
    }
    scene = Scene.model_validate(raw)
    assert (scene.video.width, scene.video.height) == (800, 600)
    assert scene.video.fps == 24
    assert scene.video.frames == 50
    assert (scene.video.first_hold, scene.video.last_hold) == (3, 7)
    with pytest.raises(ValidationError):
        Scene.model_validate({"version": 1, "video": {"bogus": 1}, "slides": [{"src": "a.png"}]})
    # Held counts may be 0 (holds off) but not negative; fps/frames must be >= 1.
    zero = Scene.model_validate({"version": 1, "video": {"first_hold": 0}, "slides": [{"src": "a.png"}]})
    assert zero.video.first_hold == 0
    with pytest.raises(ValidationError):
        Scene.model_validate({"version": 1, "video": {"first_hold": -1}, "slides": [{"src": "a.png"}]})
    with pytest.raises(ValidationError):
        Scene.model_validate({"version": 1, "video": {"fps": 0}, "slides": [{"src": "a.png"}]})


def test_caption_fade_stagger_frames() -> None:
    """Issue 309: per-caption back->front step is customizable in transition frames."""
    raw = {"version": 1, "caption_fade": {"window": 0.9, "stagger_frames": 6}, "slides": [{"src": "a.png"}]}
    scene = Scene.model_validate(raw)
    assert scene.caption_fade is not None
    assert scene.caption_fade.stagger_frames == 6
    # default leaves it None (the `stagger` fraction is used)
    d = Scene.model_validate({"version": 1, "caption_fade": {}, "slides": [{"src": "a.png"}]})
    assert d.caption_fade is not None and d.caption_fade.stagger_frames is None
