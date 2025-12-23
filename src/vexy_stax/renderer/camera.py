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

    PLAN.md §1: Final slide at Z=0 (immovable anchor), other slides at negative Z.
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
    # Z: PLAN.md §1 - final slide at Z=0, others at negative Z
    # Stack spans from -stack_depth to 0, center is at -stack_depth/2
    z_spacing = 100.0  # default if not provided
    stack_depth = (len(images) - 1) * z_spacing
    center_z = -stack_depth / 2

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


def calculate_beauty_viewpoint(
    images: list[SceneImage],
    z_spacing: float,
    fov: float,
    aspect_ratio: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Calculate cinematic beauty camera position and target.

    PLAN.md Beauty View: Camera must fit the entire FLOOR within the viewport,
    not just center on the slides. Camera is positioned to show the 3D stack
    from a 3/4 angle with the floor visible.

    Parameters
    ----------
    images:
        Scene images
    z_spacing:
        Z-spacing between slides
    fov:
        Camera field of view in degrees
    aspect_ratio:
        Canvas aspect ratio (width/height)

    Returns
    -------
    tuple[position, target]
        Camera position and look-at target as (x, y, z) tuples
    """
    if not images:
        return ((0, 0, 500), (0, 0, 0))

    # Content dimensions
    max_height = max(img.height for img in images)
    max_width = max(img.width for img in images)
    stack_depth = (len(images) - 1) * z_spacing

    # Floor geometry (PLAN.md Floor Sizing Rules)
    floor_width = max_width + 0.4 * z_spacing
    floor_length = stack_depth + 0.4 * z_spacing  # 0.2 padding each end

    # Floor center is at Y=0 (floor plane), Z = center of stack depth
    floor_center_z = -stack_depth / 2
    target = (0.0, 0.0, floor_center_z)  # Target floor center

    # Camera distance to fit floor diagonal in FOV
    floor_diagonal = math.sqrt(floor_width**2 + floor_length**2)
    fov_rad = math.radians(fov)
    half_tan = math.tan(fov_rad / 2)

    # Distance to fit floor with margin
    # pygfx interprets FOV differently - needs 1.39x theoretical distance
    PYGFX_FOV_CORRECTION = 1.39  # Empirically measured correction for pygfx FOV
    BEAUTY_FILL = 0.85  # 15% margin around floor for cinematic framing
    fit_distance = (floor_diagonal / 2) / half_tan * PYGFX_FOV_CORRECTION * (1.0 / BEAUTY_FILL)

    # Camera direction: left, above, in front (normalized)
    # X: -0.6 = to the left
    # Y: +0.5 = above floor (camera looks down)
    # Z: +0.6 = in front of floor center
    dir_x, dir_y, dir_z = -0.6, 0.5, 0.6
    norm = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
    dir_x, dir_y, dir_z = dir_x / norm, dir_y / norm, dir_z / norm

    # Camera position = floor_center + direction * distance
    cam_x = 0.0 + dir_x * fit_distance
    cam_y = 0.0 + dir_y * fit_distance
    cam_z = floor_center_z + dir_z * fit_distance

    position = (cam_x, cam_y, cam_z)
    return (position, target)


def make_camera(scene: SceneConfig, aspect_ratio: float) -> Any:
    """Instantiate a pygfx camera based on scene metadata.

    For video rendering, always computes a cinematic beauty camera position
    rather than using potentially poorly-framed saved camera positions.
    """
    mode = scene.params.camera_mode
    if mode == "orthographic":
        width = (scene.images[0].width if scene.images else 1) * DEFAULT_PADDING
        height = (scene.images[0].height if scene.images else 1) * DEFAULT_PADDING
        camera = gfx.OrthographicCamera(width=width, height=height)
    else:
        # Default FOV matches vexy-stax-js (75° perspective, 30° telephoto)
        fov = scene.params.camera_fov or (30.0 if mode == "telephoto" else 75.0)
        camera = gfx.PerspectiveCamera(fov=fov, aspect=aspect_ratio)

    # Calculate optimized beauty viewpoint (ignore saved camera for better framing)
    fov = scene.params.camera_fov or 75.0
    position, target = calculate_beauty_viewpoint(
        scene.images, scene.params.z_spacing, fov, aspect_ratio
    )

    camera.world.position = position
    camera.look_at(target)
    return camera


def calculate_content_center_with_spacing(
    images: list[SceneImage], z_spacing: float
) -> tuple[float, float, float]:
    """Calculate the center point of all images using actual z_spacing.

    PLAN.md §1: Final slide at Z=0 (immovable anchor), other slides at negative Z.
    Stack spans from -stack_depth to 0, center is at -stack_depth/2.

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

    # Z: PLAN.md §1 - final slide at Z=0, others at negative Z
    # Stack spans from -stack_depth to 0, center is at -stack_depth/2
    stack_depth = (len(images) - 1) * z_spacing
    center_z = -stack_depth / 2

    return (0.0, center_y, center_z)


def calculate_front_viewpoint(
    front_slide: SceneImage,
    canvas_width: int,
    canvas_height: int,
    fov: float = 75.0,
    *,
    front_slide_index: int = 0,
) -> FrontViewpoint:
    """Calculate camera position to fit front slide exactly to canvas.

    PLAN.md §1: Final slide at Z=0 (immovable anchor). During hero shot:
    - Final slide stays at Z=0
    - Other slides collapse to: z = -(slideCount - 1 - index) * MIN_LAYER_GAP
    - Camera positioned directly in front of the front slide (at Z=0)
    - Distance computed so larger dimension fills canvas exactly
    - Target Y is at slide center (height/2 above floor)

    Parameters
    ----------
    front_slide:
        The frontmost slide to fit (the final slide at Z=0)
    canvas_width:
        Canvas width in pixels
    canvas_height:
        Canvas height in pixels
    fov:
        Camera field of view in degrees
    front_slide_index:
        Index of the front slide (should be slideCount - 1)

    Returns
    -------
    FrontViewpoint
        Camera position, target, and collapse Z
    """
    # PLAN.md §1: Final slide is always at Z=0 (immovable anchor)
    # The front_slide_index parameter is kept for API compatibility but
    # collapse_z is always 0 since the front slide is always the final slide at Z=0
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

    # CONTINUE.md: "no part of the slide may be cut off, margins permissible only in one direction"
    # pygfx interprets FOV differently than theoretical calculation expects.
    # Content-fit means: slide fills canvas exactly when aspect ratios match,
    # otherwise margins appear in one direction only.
    #
    # Empirically measured: pygfx needs ~1.0x theoretical distance (no correction needed)
    # The previous 1.39x was overcorrected - causing 40%+ letterboxing.
    # Add minimal safety margin (2%) to prevent sub-pixel clipping at edges.
    SAFETY_MARGIN = 1.02  # 2% margin for rounding/AA artifacts
    distance = max(distance_for_height, distance_for_width, CAMERA_MIN_DISTANCE)
    distance *= SAFETY_MARGIN

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
    1. Forward: Camera moves to front view, slides collapse
    2. Hold: Camera stays at front, slides stay collapsed
    3. Return: Camera returns to start, slides restore spacing
    """

    spacing_frames: list[float]
    camera_positions: list[CameraPosition]
    camera_targets: list[CameraPosition]  # Where camera looks at each frame
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
    start_target: CameraPosition,
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
    start_target:
        Initial camera look-at target (content center at original spacing)
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
        Complete timeline with spacing, camera positions, targets, and progress
    """
    forward_frames = max(1, int(round(defaults.duration * defaults.fps)))
    hold_frames = max(0, int(round(defaults.hold * defaults.fps)))
    return_frames = (
        forward_frames if return_to_start else 0
    )  # No return if flag is False

    # Target is MIN_LAYER_GAP, but never greater than original spacing
    target_spacing = min(MIN_LAYER_GAP, spacing)

    spacing_frames: list[float] = []
    camera_positions: list[CameraPosition] = []
    camera_targets: list[CameraPosition] = []
    progress_values: list[float] = []

    front_pos = front_view.position
    front_target = front_view.target

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

        # Camera target moves from content center to front slide
        camera_targets.append(
            CameraPosition(
                x=_lerp(start_target.x, front_target.x, progress),
                y=_lerp(start_target.y, front_target.y, progress),
                z=_lerp(start_target.z, front_target.z, progress),
            )
        )

        # Hero progress for lighting/material interpolation
        progress_values.append(progress)

    # Hold phase: stay at front with target_spacing (progress = 1.0)
    for _ in range(hold_frames):
        spacing_frames.append(target_spacing)
        camera_positions.append(front_pos)
        camera_targets.append(front_target)
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

        # Camera target returns to content center
        camera_targets.append(
            CameraPosition(
                x=_lerp(front_target.x, start_target.x, progress),
                y=_lerp(front_target.y, start_target.y, progress),
                z=_lerp(front_target.z, start_target.z, progress),
            )
        )

        # Hero progress decreases back to 0
        progress_values.append(1.0 - progress)

    return HeroTimeline(
        spacing_frames=spacing_frames,
        camera_positions=camera_positions,
        camera_targets=camera_targets,
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
