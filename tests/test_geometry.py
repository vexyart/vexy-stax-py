# this_file: tests/test_geometry.py
"""Tests for engine-agnostic geometry math (SPEC.md §3).

Fixture vectors are kept explicit so the JS ``geometry.js`` can later match them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_stax import geometry as g
from vexy_stax.scene import Scene, load_scene

EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"

EASINGS = ["linear", "easeInOutCubic", "easeOutCubic", "easeInCubic"]


@pytest.fixture
def scene() -> Scene:
    return load_scene(EXAMPLE)


@pytest.mark.parametrize("name", EASINGS)
def test_ease_endpoints(name: str) -> None:
    assert g.ease(name, 0.0) == pytest.approx(0.0)
    assert g.ease(name, 1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("name", EASINGS)
def test_ease_clamps(name: str) -> None:
    assert g.ease(name, -5.0) == pytest.approx(0.0)
    assert g.ease(name, 5.0) == pytest.approx(1.0)


def test_ease_midpoint_values() -> None:
    assert g.ease("linear", 0.5) == pytest.approx(0.5)
    assert g.ease("easeInOutCubic", 0.5) == pytest.approx(0.5)
    assert g.ease("easeInCubic", 0.5) == pytest.approx(0.125)
    assert g.ease("easeOutCubic", 0.5) == pytest.approx(0.875)


def test_ease_unknown_raises() -> None:
    with pytest.raises(ValueError):
        g.ease("bogus", 0.5)


def test_interpolate_opacity_lerps(scene: Scene) -> None:
    halftone = scene.slides[6]  # expanded=1.0, compact=0.4
    assert g.interpolate_opacity(halftone, 0.0) == pytest.approx(0.4)
    assert g.interpolate_opacity(halftone, 1.0) == pytest.approx(1.0)
    assert g.interpolate_opacity(halftone, 0.5) == pytest.approx(0.7)


def test_interpolate_opacity_scalar(scene: Scene) -> None:
    source = scene.slides[0]  # scalar 1.0
    assert g.interpolate_opacity(source, 0.0) == pytest.approx(1.0)
    assert g.interpolate_opacity(source, 0.5) == pytest.approx(1.0)


def test_stack_depth_expanded_vs_compact(scene: Scene) -> None:
    n = len(scene.slides)  # 8
    compact = g.stack_depth(scene, "compact")
    expanded = g.stack_depth(scene, "expanded")
    assert compact == pytest.approx((n - 1) * g.MIN_GAP)  # 7 * 3 = 21
    assert expanded == pytest.approx((n - 1) * scene.camera.gap)  # 7 * 480 = 3360
    assert expanded > compact


def test_camera_near_scales_with_distance(scene: Scene) -> None:
    cam = g.expanded_camera(scene)
    # distance is |position - target|
    dist = sum((p - t) ** 2 for p, t in zip(cam.position, cam.target)) ** 0.5
    assert cam.near == pytest.approx(max(1.0, dist * 0.005))
    assert cam.near > 1.0  # large deck -> near above the floor of 1.0


def test_compact_camera_head_on_plus_z(scene: Scene) -> None:
    cam = g.compact_camera(scene)
    # head-on: camera sits on +Z in front of the target (toward the viewer)
    assert cam.position[2] > cam.target[2]
    assert cam.position[0] == pytest.approx(cam.target[0])
    assert cam.position[1] == pytest.approx(cam.target[1])
    # distance = 90% of viewport width (1246)
    assert cam.position[2] - cam.target[2] == pytest.approx(0.90 * scene.size.width)


def test_expanded_camera_frames_deck(scene: Scene) -> None:
    cam = g.expanded_camera(scene)
    # target is the deck center; elevation 0 keeps the camera at deck height.
    assert cam.target == pytest.approx((0.0, 0.0, -g.stack_depth(scene, "expanded") / 2.0))
    assert cam.position[1] == pytest.approx(0.0)  # elevation 0
    # azimuth 60 swings the camera toward -X and toward the viewer (+Z).
    assert cam.position[0] < 0.0
    assert cam.position[2] > cam.target[2]


def test_plate_gaps_fallback(scene: Scene) -> None:
    gaps = g.plate_gaps(scene)
    assert len(gaps) == len(scene.slides)
    assert all(x == pytest.approx(scene.camera.gap) for x in gaps)


def test_frame_plan_length(scene: Scene) -> None:
    # expand_collapse: 2 legs; duration 3.0 * 30 = 90 frames/leg; wait 1.0 * 30 = 30
    plan = g.frame_plan(scene)
    expected = 2 * (round(3.0 * 30) + round(1.0 * 30))  # 2 * (90 + 30) = 240
    assert len(plan) == expected == 240


def test_frame_plan_empty_without_transition(scene: Scene) -> None:
    scene.transition = None
    assert g.frame_plan(scene) == []


def test_frame_plan_endpoints_opacity(scene: Scene) -> None:
    plan = g.frame_plan(scene)
    halftone_idx = 6
    # expand_collapse starts compact (t=0): halftone opacity 0.4
    assert plan[0].opacities[halftone_idx] == pytest.approx(0.4)
    # at the end of leg 1 (frame 90 = first hold frame), fully expanded: 1.0
    assert plan[90].opacities[halftone_idx] == pytest.approx(1.0)
