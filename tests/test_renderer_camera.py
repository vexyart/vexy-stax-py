# this_file: tests/test_renderer_camera.py

from __future__ import annotations

import numpy as np
import pygfx as gfx
import pytest

from vexy_stax.config import MIN_LAYER_GAP, AnimationDefaults
from vexy_stax.models import SceneCamera, SceneConfig, SceneImage, SceneParams
from vexy_stax.renderer.camera import (
    CameraPosition,
    FrontViewpoint,
    build_hero_timeline,
    build_spacing_timeline,
    calculate_front_viewpoint,
    ease_power2_in_out,
    make_camera,
)


def _scene_config(
    camera_mode: str = "perspective", camera: SceneCamera | None = None
) -> SceneConfig:
    params = SceneParams(
        z_spacing=0.25,
        bg_color="#000000",
        transparent_bg=False,
        camera_mode=camera_mode,
        camera_fov=None,
        camera_zoom=None,
    )
    image = SceneImage(
        filename="layer.png",
        width=400,
        height=300,
        pixels=np.zeros((1, 1, 4), dtype=np.uint8),
    )
    return SceneConfig(version="1.0", params=params, images=[image] * 3, camera=camera)


def test_make_camera_when_perspective_then_uses_default_fov() -> None:
    scene = _scene_config(camera_mode="perspective")
    camera = make_camera(scene, aspect_ratio=16 / 9)

    assert isinstance(camera, gfx.PerspectiveCamera)
    # Default FOV matches vexy-stax-js (75° for perspective)
    assert camera.fov == pytest.approx(75.0)
    assert camera.aspect == pytest.approx(16 / 9)
    assert camera.world.position[2] > 0


def test_make_camera_when_telephoto_then_uses_narrower_fov() -> None:
    scene = _scene_config(camera_mode="telephoto")
    camera = make_camera(scene, aspect_ratio=1.0)

    assert isinstance(camera, gfx.PerspectiveCamera)
    assert camera.fov == pytest.approx(30.0)


def test_make_camera_when_orthographic_then_respects_image_size() -> None:
    scene = _scene_config(camera_mode="orthographic")
    camera = make_camera(scene, aspect_ratio=4 / 3)

    assert isinstance(camera, gfx.OrthographicCamera)
    assert camera.width > 0
    assert camera.height > 0


def test_make_camera_when_scene_has_camera_then_beauty_viewpoint_computed() -> None:
    """make_camera now always computes cinematic beauty viewpoint.

    Saved camera positions from JS may be poorly framed, so we compute an
    optimal beauty position based on content dimensions and spacing.
    """
    camera = SceneCamera(x=1.0, y=2.0, z=3.0)
    scene = _scene_config(camera_mode="perspective", camera=camera)
    result = make_camera(scene, aspect_ratio=1.0)

    # Camera should be positioned at computed beauty viewpoint, not saved position
    # Position will be offset from center for 3/4 angle view
    assert result.world.position[0] != pytest.approx(1.0)  # Not using saved X
    assert result.world.position[2] > 0  # Camera should be in front of content


def test_ease_power2_in_out_when_midpoint_then_returns_smooth_value() -> None:
    assert ease_power2_in_out(0.0) == 0.0
    assert ease_power2_in_out(1.0) == 1.0
    assert ease_power2_in_out(0.5) == pytest.approx(0.5)


def test_build_spacing_timeline_when_defaults_then_monotonic_and_collapses_to_min_gap() -> (
    None
):
    """Spacing timeline collapses to MIN_LAYER_GAP (not 0) to prevent z-fighting."""
    defaults = AnimationDefaults(fps=30, duration=2.0, hold=0.5, easing="power2.inOut")
    # Use spacing larger than MIN_LAYER_GAP to test collapse behavior
    timeline = build_spacing_timeline(spacing=100.0, defaults=defaults)

    assert len(timeline.frames) == 75, "Duration (2s) + hold (0.5s) at 30fps"
    assert timeline.frames[0] == pytest.approx(100.0)
    # Should collapse to MIN_LAYER_GAP, not 0
    assert timeline.frames[-1] == pytest.approx(MIN_LAYER_GAP)
    monotonic = all(
        curr >= nxt - 1e-6 for curr, nxt in zip(timeline.frames, timeline.frames[1:])
    )
    assert monotonic, "Spacing should never increase"


def test_build_spacing_timeline_when_spacing_less_than_min_gap_then_stays_constant() -> (
    None
):
    """When spacing is already smaller than MIN_LAYER_GAP, stays at original spacing."""
    defaults = AnimationDefaults(fps=30, duration=1.0, hold=0.0, easing="power2.inOut")
    # Use spacing smaller than MIN_LAYER_GAP
    timeline = build_spacing_timeline(spacing=1.0, defaults=defaults)

    # Should stay at original spacing (no increase to MIN_LAYER_GAP)
    assert timeline.frames[0] == pytest.approx(1.0)
    assert timeline.frames[-1] == pytest.approx(1.0)


def test_build_spacing_timeline_when_duration_zero_then_single_frame() -> None:
    """With zero duration, we get at least 1 frame (graceful handling)."""
    defaults = AnimationDefaults(fps=30, duration=0.0, hold=0.0, easing="power2.inOut")
    timeline = build_spacing_timeline(spacing=100.0, defaults=defaults)
    # At least 1 frame even with zero duration
    assert len(timeline.frames) >= 1


def test_calculate_front_viewpoint_when_slide_given_then_returns_fit_position() -> None:
    """Front viewpoint should position camera to fit slide exactly to canvas."""
    slide = SceneImage(
        filename="test.png",
        width=800,
        height=600,
        pixels=np.zeros((600, 800, 4), dtype=np.uint8),
    )
    result = calculate_front_viewpoint(
        slide, canvas_width=1920, canvas_height=1080, fov=75.0
    )

    assert isinstance(result, FrontViewpoint)
    assert result.collapse_z == 0.0
    assert result.target.z == 0.0
    assert result.position.z > 0  # Camera in front of slide
    assert result.position.x == 0.0  # Centered horizontally
    # Camera Y is at slide center (height/2) for proper framing
    # (slide sits on floor at Y=0, so its center is at Y=height/2)
    assert result.position.y == 300.0  # Centered on slide (600/2)
    assert result.target.y == 300.0  # Target at slide center


def test_calculate_front_viewpoint_when_tall_slide_then_needs_more_distance() -> None:
    """Tall slides on wide canvas need more distance to fit vertically."""
    wide = SceneImage(
        filename="wide.png",
        width=1600,
        height=400,
        pixels=np.zeros((1, 1, 4), dtype=np.uint8),
    )
    tall = SceneImage(
        filename="tall.png",
        width=400,
        height=1600,
        pixels=np.zeros((1, 1, 4), dtype=np.uint8),
    )

    wide_result = calculate_front_viewpoint(wide, 1920, 1080, fov=75.0)
    tall_result = calculate_front_viewpoint(tall, 1920, 1080, fov=75.0)

    # For 16:9 canvas (1920x1080), tall slide needs more distance to fit vertically
    assert tall_result.position.z > wide_result.position.z


def test_build_hero_timeline_when_defaults_then_has_forward_hold_return() -> None:
    """Hero timeline should have forward, hold, and return phases.

    Spacing collapses to MIN_LAYER_GAP (not 0) to prevent z-fighting.
    """
    defaults = AnimationDefaults(fps=30, duration=1.0, hold=0.5, easing="power2.inOut")
    start_camera = CameraPosition(x=0, y=0, z=1000)
    start_target = CameraPosition(x=0, y=0, z=50)  # Content center at original spacing
    front_view = FrontViewpoint(
        position=CameraPosition(x=0, y=0, z=500),
        target=CameraPosition(x=0, y=0, z=0),
        collapse_z=0.0,
    )

    timeline = build_hero_timeline(
        spacing=100.0,
        start_camera=start_camera,
        start_target=start_target,
        front_view=front_view,
        defaults=defaults,
    )

    # Forward (30) + Hold (15) + Return (30) = 75 frames
    assert len(timeline.spacing_frames) == 75
    assert len(timeline.camera_positions) == 75
    assert len(timeline.camera_targets) == 75
    assert len(timeline.progress_values) == 75

    # Check forward phase starts at original values
    assert timeline.spacing_frames[0] == pytest.approx(100.0)
    assert timeline.camera_positions[0].z == pytest.approx(1000.0)
    assert timeline.camera_targets[0].z == pytest.approx(50.0)

    # Check hold phase has collapsed values (frame 30 is start of hold)
    # Spacing collapses to MIN_LAYER_GAP (not 0) to prevent z-fighting
    hold_start = 30
    assert timeline.spacing_frames[hold_start - 1] == pytest.approx(
        MIN_LAYER_GAP, abs=1e-3
    )
    assert timeline.camera_positions[hold_start - 1].z == pytest.approx(500.0, abs=1e-3)
    assert timeline.camera_targets[hold_start - 1].z == pytest.approx(0.0, abs=1e-3)

    # Check return phase ends at original values
    assert timeline.spacing_frames[-1] == pytest.approx(100.0)
    assert timeline.camera_positions[-1].z == pytest.approx(1000.0)
    assert timeline.camera_targets[-1].z == pytest.approx(50.0)


def test_build_hero_timeline_progress_values_when_forward_hold_return_then_0_to_1_to_0() -> (
    None
):
    """Progress values should be 0→1 (forward), 1 (hold), 1→0 (return).

    Progress is used for lighting/material interpolation at hero shot culmination.
    """
    defaults = AnimationDefaults(fps=30, duration=1.0, hold=0.5, easing="power2.inOut")
    start_camera = CameraPosition(x=0, y=0, z=1000)
    start_target = CameraPosition(x=0, y=0, z=50)
    front_view = FrontViewpoint(
        position=CameraPosition(x=0, y=0, z=500),
        target=CameraPosition(x=0, y=0, z=0),
        collapse_z=0.0,
    )

    timeline = build_hero_timeline(
        spacing=100.0,
        start_camera=start_camera,
        start_target=start_target,
        front_view=front_view,
        defaults=defaults,
    )

    # Forward phase: starts at 0
    assert timeline.progress_values[0] == pytest.approx(0.0)

    # End of forward phase (frame 29): should be at 1.0
    assert timeline.progress_values[29] == pytest.approx(1.0)

    # Hold phase (frames 30-44): should stay at 1.0
    for i in range(30, 45):
        assert timeline.progress_values[i] == pytest.approx(1.0), (
            f"Frame {i} should be 1.0"
        )

    # Return phase starts at 1.0, ends at 0.0
    assert timeline.progress_values[45] == pytest.approx(1.0)
    assert timeline.progress_values[-1] == pytest.approx(0.0)
