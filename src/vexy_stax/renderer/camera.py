# this_file: vexy-stax-py/src/vexy_stax/renderer/camera.py
"""Camera factories and hero timeline easing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pygfx as gfx

from ..config import DEFAULT_PADDING, FLOOR_Y, MIN_LAYER_GAP, AnimationDefaults
from ..models import SceneConfig, SceneImage

# Camera minimum distance to avoid clipping
CAMERA_MIN_DISTANCE = 100.0


def calculate_content_center(images: list[SceneImage]) -> tuple[float, float, float]:
    """Calculate the center point of all images in the scene.

    Slides sit on floor (Y=0), so their center Y is height/2.
    Returns the center of the bounding box containing all slides.

    Parameters
    ----------
    images:
        List of scene images with width/height properties

    Returns
    -------
    tuple[float, float, float]
        (x, y, z) coordinates of the content center
    """
    if not images:
        return (0.0, 0.0, 0.0)

    # Find tallest slide
    max_height = max((img.height for img in images), default=1)

    # Center Y is at the vertical middle of the tallest slide
    # (slides sit on floor at Y=0, so tallest slide center is at max_height/2)
    center_y = FLOOR_Y + max_height / 2

    # X is always 0 (slides are centered horizontally)
    # Z is the middle of the stack
    z_spacing = 100.0  # default if not provided
    stack_depth = len(images) * z_spacing
    center_z = stack_depth / 2

    return (0.0, center_y, center_z)


@dataclass(slots=True, frozen=True)
class CameraPosition:
    """3D camera position."""

    x: float
    y: float
    z: float


@dataclass(slots=True, frozen=True)
class FrontViewpoint:
    """Front view camera configuration for hero shot."""

    position: CameraPosition  # Camera position
    target: CameraPosition  # Look-at target
    collapse_z: float  # Z position where slides collapse


def ease_power2_in_out(t: float) -> float:
    """Smooth in/out easing mirroring GSAP ``power2.inOut``."""

    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if t < 0.5:
        return 2 * (t**2)
    return 1 - 2 * ((1 - t) ** 2)


def make_camera(scene: SceneConfig, aspect_ratio: float) -> Any:
    """Instantiate a pygfx camera based on scene metadata."""
    import math

    mode = scene.params.camera_mode
    if mode == "orthographic":
        width = (scene.images[0].width if scene.images else 1) * DEFAULT_PADDING
        height = (scene.images[0].height if scene.images else 1) * DEFAULT_PADDING
        camera = gfx.OrthographicCamera(width=width, height=height)
    else:
        # Default FOV matches vexy-stax-js (75° perspective, 30° telephoto)
        fov = scene.params.camera_fov or (30.0 if mode == "telephoto" else 75.0)
        camera = gfx.PerspectiveCamera(fov=fov, aspect=aspect_ratio)

    # Calculate content center for camera target
    content_center = calculate_content_center_with_spacing(
        scene.images, scene.params.z_spacing
    )

    if scene.camera is not None:
        camera.world.position = (scene.camera.x, scene.camera.y, scene.camera.z)
    else:
        # Calculate camera distance to fit largest image in view
        max_height = max((img.height for img in scene.images), default=1)
        max_width = max((img.width for img in scene.images), default=1)

        # Use whichever dimension requires more distance
        fov_rad = math.radians(fov if mode != "orthographic" else 75.0)
        dist_for_height = (max_height / 2) / math.tan(fov_rad / 2)
        dist_for_width = (max_width / 2) / (aspect_ratio * math.tan(fov_rad / 2))
        fit_distance = max(dist_for_height, dist_for_width)

        # Add stack depth and padding
        stack_depth = len(scene.images) * scene.params.z_spacing
        camera_z = fit_distance * DEFAULT_PADDING + stack_depth

        camera.world.position = (content_center[0], content_center[1], camera_z)

    # Look at content center (not origin) for proper framing
    camera.look_at(content_center)
    return camera


def calculate_content_center_with_spacing(
    images: list[SceneImage], z_spacing: float
) -> tuple[float, float, float]:
    """Calculate the center point of all images using actual z_spacing.

    Parameters
    ----------
    images:
        List of scene images with width/height properties
    z_spacing:
        Z-spacing between slides

    Returns
    -------
    tuple[float, float, float]
        (x, y, z) coordinates of the content center
    """
    if not images:
        return (0.0, 0.0, 0.0)

    # Find tallest slide
    max_height = max((img.height for img in images), default=1)

    # Center Y is at the vertical middle of the tallest slide
    center_y = FLOOR_Y + max_height / 2

    # Z is the middle of the stack
    stack_depth = (len(images) - 1) * z_spacing
    center_z = stack_depth / 2

    return (0.0, center_y, center_z)


def calculate_front_viewpoint(
    front_slide: SceneImage,
    canvas_width: int,
    canvas_height: int,
    fov: float = 75.0,
) -> FrontViewpoint:
    """Calculate camera position to fit front slide exactly to canvas.

    Mirrors the JS calculateFrontViewpoint() logic:
    - Slides collapse to z=0 (origin)
    - Camera positioned directly in front at calculated distance
    - Distance computed so larger dimension fills canvas exactly
    - Target Y is at slide center (height/2 above floor)

    Parameters
    ----------
    front_slide:
        The frontmost slide to fit
    canvas_width:
        Canvas width in pixels
    canvas_height:
        Canvas height in pixels
    fov:
        Camera field of view in degrees

    Returns
    -------
    FrontViewpoint
        Camera position, target, and collapse Z
    """
    # Slides collapse to z=0
    collapse_z = 0.0

    # Get slide dimensions
    width = front_slide.width or 1
    height = front_slide.height or 1

    # Target Y is at slide center (slide sits on floor at Y=0)
    target_y = FLOOR_Y + height / 2

    # Target is at slide center at collapsed Z
    target = CameraPosition(x=0.0, y=target_y, z=collapse_z)

    # Calculate camera distance to fit slide to canvas (strict fit, no padding)
    aspect = canvas_width / canvas_height
    fov_rad = math.radians(fov)

    half_vertical_tan = max(math.tan(fov_rad / 2), 1e-6)
    horizontal_fov = 2 * math.atan(half_vertical_tan * aspect)
    half_horizontal_tan = max(math.tan(horizontal_fov / 2), 1e-6)

    # Distance to fit height and width
    distance_for_height = (height / 2) / half_vertical_tan
    distance_for_width = (width / 2) / half_horizontal_tan

    # Use whichever requires more distance (strict fit, padding = 1.0)
    distance = max(distance_for_height, distance_for_width, CAMERA_MIN_DISTANCE)

    # Camera directly in front of collapsed stack, at same Y as target
    position = CameraPosition(x=0.0, y=target_y, z=collapse_z + distance)

    return FrontViewpoint(position=position, target=target, collapse_z=collapse_z)


@dataclass(slots=True, frozen=True)
class SpacingTimeline:
    frames: list[float]
    fps: int

    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps


@dataclass(slots=True, frozen=True)
class HeroTimeline:
    """Complete hero shot timeline with spacing and camera positions.

    The animation has three phases:
    1. Forward: Camera moves to front view, slides collapse to z=0
    2. Hold: Camera stays at front, slides stay collapsed
    3. Return: Camera returns to start, slides restore spacing
    """

    spacing_frames: list[float]
    camera_positions: list[CameraPosition]
    progress_values: list[float]  # 0→1→1→0 for lighting/material interpolation
    fps: int

    @property
    def duration(self) -> float:
        return len(self.spacing_frames) / self.fps


def build_spacing_timeline(
    *,
    spacing: float,
    defaults: AnimationDefaults,
) -> SpacingTimeline:
    """Build spacing timeline that collapses to MIN_LAYER_GAP (not zero).

    This prevents z-fighting when slides are fully collapsed during hero shot.
    If spacing is already smaller than MIN_LAYER_GAP, collapse to spacing instead.
    """
    total_frames = max(1, int(round(defaults.duration * defaults.fps)))
    hold_frames = max(0, int(round(defaults.hold * defaults.fps)))

    # Target is MIN_LAYER_GAP, but never greater than original spacing
    # (to ensure monotonic decrease)
    target_spacing = min(MIN_LAYER_GAP, spacing)

    # Collapse from original spacing to target
    frames: list[float] = []
    for index in range(total_frames):
        t = index / max(total_frames - 1, 1)
        progress = ease_power2_in_out(t)
        # Interpolate from spacing down to target
        collapsed_value = spacing * (1 - progress) + target_spacing * progress
        frames.append(collapsed_value)

    # Hold phase at target spacing
    frames.extend([target_spacing] * hold_frames)

    # Verify monotonic decrease
    for earlier, later in zip(frames, frames[1:]):
        if later > earlier + 1e-6:
            raise ValueError("Hero spacing timeline must be non-increasing")

    return SpacingTimeline(frames=frames, fps=defaults.fps)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def build_hero_timeline(
    *,
    spacing: float,
    start_camera: CameraPosition,
    front_view: FrontViewpoint,
    defaults: AnimationDefaults,
    return_to_start: bool = True,
) -> HeroTimeline:
    """Build complete hero shot timeline with camera animation.

    Creates a timeline that:
    1. Forward phase: Camera moves to front, spacing collapses to MIN_LAYER_GAP
    2. Hold phase: Camera stays at front, spacing stays at MIN_LAYER_GAP
    3. Return phase (optional): Camera returns to start, spacing restores

    Uses MIN_LAYER_GAP (or smaller if original spacing is smaller) to prevent
    z-fighting during hero shot.

    The progress_values track animation culmination (0→1→1→0 or 0→1→1) for smooth
    lighting and material transitions. At culmination (progress=1), lighting
    becomes flat and material switches to basic for composite-like appearance.

    Parameters
    ----------
    spacing:
        Original z-spacing between slides
    start_camera:
        Initial camera position (beauty view)
    front_view:
        Target front view configuration
    defaults:
        Animation timing parameters
    return_to_start:
        If True (default), animation returns to starting position after hold.
        If False, animation ends at hero view (front position, collapsed spacing).

    Returns
    -------
    HeroTimeline
        Complete timeline with spacing, camera positions, and progress per frame
    """
    forward_frames = max(1, int(round(defaults.duration * defaults.fps)))
    hold_frames = max(0, int(round(defaults.hold * defaults.fps)))
    return_frames = forward_frames if return_to_start else 0  # No return if flag is False

    # Target is MIN_LAYER_GAP, but never greater than original spacing
    target_spacing = min(MIN_LAYER_GAP, spacing)

    spacing_frames: list[float] = []
    camera_positions: list[CameraPosition] = []
    progress_values: list[float] = []

    front_pos = front_view.position

    # Forward phase: start → front (progress 0 → 1)
    for i in range(forward_frames):
        t = i / max(forward_frames - 1, 1)
        progress = ease_power2_in_out(t)

        # Spacing collapses to target_spacing
        collapsed_value = spacing * (1 - progress) + target_spacing * progress
        spacing_frames.append(collapsed_value)

        # Camera moves to front position
        camera_positions.append(
            CameraPosition(
                x=_lerp(start_camera.x, front_pos.x, progress),
                y=_lerp(start_camera.y, front_pos.y, progress),
                z=_lerp(start_camera.z, front_pos.z, progress),
            )
        )

        # Hero progress for lighting/material interpolation
        progress_values.append(progress)

    # Hold phase: stay at front with target_spacing (progress = 1.0)
    for _ in range(hold_frames):
        spacing_frames.append(target_spacing)
        camera_positions.append(front_pos)
        progress_values.append(1.0)

    # Return phase: front → start (progress 1 → 0)
    for i in range(return_frames):
        t = i / max(return_frames - 1, 1)
        progress = ease_power2_in_out(t)

        # Spacing restores from target_spacing to original
        restored_value = target_spacing * (1 - progress) + spacing * progress
        spacing_frames.append(restored_value)

        # Camera returns to start position
        camera_positions.append(
            CameraPosition(
                x=_lerp(front_pos.x, start_camera.x, progress),
                y=_lerp(front_pos.y, start_camera.y, progress),
                z=_lerp(front_pos.z, start_camera.z, progress),
            )
        )

        # Hero progress decreases back to 0
        progress_values.append(1.0 - progress)

    return HeroTimeline(
        spacing_frames=spacing_frames,
        camera_positions=camera_positions,
        progress_values=progress_values,
        fps=defaults.fps,
    )


__all__ = [
    "CAMERA_MIN_DISTANCE",
    "CameraPosition",
    "FrontViewpoint",
    "HeroTimeline",
    "SpacingTimeline",
    "build_hero_timeline",
    "build_spacing_timeline",
    "calculate_content_center",
    "calculate_content_center_with_spacing",
    "calculate_front_viewpoint",
    "ease_power2_in_out",
    "make_camera",
]
