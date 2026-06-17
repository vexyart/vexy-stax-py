# this_file: src/vexy_stax/geometry.py
"""Engine-agnostic view geometry per SPEC.md §3.

Pure functions only: math + stdlib (+ numpy allowed). No rendering deps. The
three Python engines and the JS renderer consume these results so they agree.

Coordinate convention (three.js Y-up — per SPEC.md §1, §3; matched by both the
Blender render script and the JS three.js stage so all renderers agree):
- ``X`` = plate width, centered at ``X = 0``.
- ``Y`` = vertical (up). Plates are centered at ``Y = 0`` (vertical middle of the
  tallest slide); the floor sits just below ``Y = -h/2``.
- ``Z`` = depth/stacking. The front plate is at ``Z = 0``, index 0 (farthest) at
  ``Z = -stack_depth``; ``+Z`` points toward the viewer. The deck center is at
  ``Z = -stack_depth/2``.
- Both cameras look toward the deck center. The compact camera sits head-on on
  ``+Z``; the expanded camera orbits to an azimuth/elevation around the target.
- Framing assumes plates share the scene canvas size (``scene.size``); engines may
  scale individual plate meshes to their true pixel dimensions, but the camera fit
  is computed from ``scene.size`` so Python and JS stay numerically identical.
- Plate width/height in points == pixel dimensions of the source image.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vexy_stax.scene import Scene, View

MIN_GAP = 3.0
FILL = 0.85


@dataclass(frozen=True)
class CameraPose:
    """A perspective camera placement."""

    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float  # degrees
    near: float


@dataclass(frozen=True)
class FrameState:
    """One animation frame: camera pose + per-slide spacing and opacity."""

    camera: CameraPose
    gaps: list[float]  # effective gap before each slide (slide 0's gap is unused)
    opacities: list[float]


def plate_gaps(scene: Scene) -> list[float]:
    """Per-slide gap (points), falling back to ``camera.gap`` when unset."""
    return [scene.camera.gap if s.gap is None else s.gap for s in scene.slides]


def stack_depth(scene: Scene, view: View) -> float:
    """Total deck depth along ``Z``.

    Compact collapses every gap to ``MIN_GAP``; expanded uses per-slide gaps.
    Depth is the sum of the (N-1) inter-plate gaps.
    """
    n = len(scene.slides)
    if n <= 1:
        return 0.0
    if view == "compact":
        return (n - 1) * MIN_GAP
    # gaps[0] is the gap before slide 0 (no predecessor), so sum gaps[1:].
    return sum(plate_gaps(scene)[1:])


def _stack_positions(gaps: list[float]) -> list[float]:
    """Per-plate ``Z`` (front plate at 0, index 0 at ``-stack_depth``).

    ``gaps[i]`` is the gap in front of plate ``i`` (``gaps[0]`` has no
    predecessor and is unused). Matches the engines' plate placement.
    """
    n = len(gaps)
    if n == 0:
        return []
    depth = sum(gaps[1:])
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + gaps[i])
    return [c - depth for c in cum]


def _sub(a: tuple, b: tuple) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: tuple, b: tuple) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple, b: tuple) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normalize(a: tuple) -> tuple[float, float, float]:
    n = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _parse_distance(distance: float | str, viewport_width: float) -> float:
    """Resolve a distance spec to absolute points.

    Numbers (or numeric strings) are absolute points; a ``"P%"`` string is that
    percentage of the viewport width.
    """
    if isinstance(distance, (int, float)):
        return float(distance)
    text = distance.strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100.0 * viewport_width
    return float(text)


def expanded_camera(scene: Scene) -> CameraPose:
    """Angled hero camera framing the expanded *deck* (SPEC.md §3, legacy SCENE §8/§9).

    Unlike the legacy floor-diagonal fit (which let a deep floor shrink the plates
    to a speck), this fits the deck's *plate* bounding box: the eight plate corners
    are projected onto the camera right/up axes and the distance is chosen so the
    deck fills ``FILL`` of the frame on its tighter axis. Plate size is taken from
    ``scene.size`` (see module docstring) so JS and Python agree exactly.
    """
    cam = scene.camera
    depth = stack_depth(scene, "expanded")
    target = (0.0, 0.0, -depth / 2.0)

    # Direction target->camera (azimuth swings toward -X, elevation lifts +Y,
    # head-on is along +Z toward the viewer).
    az = math.radians(cam.angle)
    el = math.radians(cam.elevation)
    to_cam = _normalize(
        (
            -math.sin(az) * math.cos(el),
            math.sin(el),
            math.cos(az) * math.cos(el),
        )
    )
    look = (-to_cam[0], -to_cam[1], -to_cam[2])  # camera -> target

    # Camera right/up basis (right-handed, world up = +Y).
    up_world = (0.0, 1.0, 0.0)
    right = _cross(look, up_world)
    right = _normalize(right) if abs(_dot(look, up_world)) < 0.999 else (1.0, 0.0, 0.0)
    up = _normalize(_cross(right, look))

    # Deck plate corners (uniform plate = scene.size), stacked along Z.
    half_w_plate = scene.size.width / 2.0
    half_h_plate = scene.size.height / 2.0
    z_positions = _stack_positions(plate_gaps(scene))
    half_w = 0.0
    half_h = 0.0
    for z in z_positions:
        for sx in (-half_w_plate, half_w_plate):
            for sy in (-half_h_plate, half_h_plate):
                rel = _sub((sx, sy, z), target)
                half_w = max(half_w, abs(_dot(rel, right)))
                half_h = max(half_h, abs(_dot(rel, up)))

    hfov = math.radians(cam.fov)
    aspect = scene.size.width / scene.size.height
    vfov = 2.0 * math.atan(math.tan(hfov / 2.0) / aspect)
    d_w = half_w / (FILL * math.tan(hfov / 2.0))
    d_h = half_h / (FILL * math.tan(vfov / 2.0))
    distance = max(d_w, d_h)
    near = max(1.0, distance * 0.005)
    position = (
        target[0] + to_cam[0] * distance,
        target[1] + to_cam[1] * distance,
        target[2] + to_cam[2] * distance,
    )
    return CameraPose(position=position, target=target, fov=cam.fov, near=near)


def compact_camera(scene: Scene) -> CameraPose:
    """Head-on camera on ``+Z`` aimed at the deck center.

    ``distance`` is parsed as "P%" of viewport width or absolute points. Near
    plane scales with distance to avoid depth-buffer flashing during animation.
    """
    cam = scene.camera
    depth = stack_depth(scene, "compact")
    target = (0.0, 0.0, -depth / 2.0)
    distance = _parse_distance(cam.distance, float(scene.size.width))
    near = max(1.0, distance * 0.005)
    position = (target[0], target[1], target[2] + distance)
    return CameraPose(position=position, target=target, fov=cam.fov, near=near)


def ease(name: str, t: float) -> float:
    """Evaluate a shared easing curve at ``t`` (clamped to [0, 1])."""
    t = max(0.0, min(1.0, t))
    if name == "linear":
        return t
    if name == "easeInCubic":
        return t * t * t
    if name == "easeOutCubic":
        u = 1.0 - t
        return 1.0 - u * u * u
    if name == "easeInOutCubic":
        if t < 0.5:
            return 4.0 * t * t * t
        u = -2.0 * t + 2.0
        return 1.0 - (u * u * u) / 2.0
    raise ValueError(f"Unknown easing: {name!r}")


def interpolate_opacity(slide, t_expanded: float) -> float:
    """Opacity at morph progress ``t_expanded`` in [0, 1] (0=compact, 1=expanded).

    Lerps the compact and expanded per-view values. ``t_expanded`` is the eased
    morph factor toward the expanded view.
    """
    t = max(0.0, min(1.0, t_expanded))
    lo = slide.resolved_opacity("compact")
    hi = slide.resolved_opacity("expanded")
    value = lo + (hi - lo) * t
    return max(0.0, min(1.0, value))


def _lerp3(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _pose_at(scene: Scene, compact: CameraPose, expanded: CameraPose, t: float) -> CameraPose:
    """Interpolated camera pose at morph factor ``t`` (0=compact, 1=expanded)."""
    return CameraPose(
        position=_lerp3(compact.position, expanded.position, t),
        target=_lerp3(compact.target, expanded.target, t),
        fov=compact.fov + (expanded.fov - compact.fov) * t,
        near=compact.near + (expanded.near - compact.near) * t,
    )


def _frame_state(scene: Scene, compact: CameraPose, expanded: CameraPose, t: float) -> FrameState:
    """Build a FrameState at morph factor ``t`` (already eased)."""
    expanded_gaps = plate_gaps(scene)
    gaps = [MIN_GAP + (g - MIN_GAP) * t for g in expanded_gaps]
    opacities = [interpolate_opacity(s, t) for s in scene.slides]
    return FrameState(camera=_pose_at(scene, compact, expanded, t), gaps=gaps, opacities=opacities)


# Each transition is a sequence of legs; each leg is (from, to) morph endpoints
# expressed as morph factors (0=compact, 1=expanded). A "wait" hold is inserted
# at the far end of single-direction transitions, between legs for round-trips.
_LEGS: dict[str, list[tuple[float, float]]] = {
    "expand": [(0.0, 1.0)],
    "collapse": [(1.0, 0.0)],
    "expand_collapse": [(0.0, 1.0), (1.0, 0.0)],
    "collapse_expand": [(1.0, 0.0), (0.0, 1.0)],
}


def frame_plan(scene: Scene) -> list[FrameState]:
    """Per-frame states for ``scene.transition`` (empty when no transition).

    Layout: each leg renders ``round(duration*fps)`` frames; a hold of
    ``round(wait*fps)`` frames is inserted at the far end of each leg (i.e. after
    reaching the destination of every leg). Total length is therefore
    ``legs * (round(duration*fps) + round(wait*fps))``.
    """
    tr = scene.transition
    if tr is None:
        return []
    compact = compact_camera(scene)
    expanded = expanded_camera(scene)
    leg_frames = round(tr.duration * tr.fps)
    wait_frames = round(tr.wait * tr.fps)
    legs = _LEGS[tr.kind]

    states: list[FrameState] = []
    for start, end in legs:
        for i in range(leg_frames):
            # progress across the leg in [0, 1)
            p = i / leg_frames if leg_frames else 0.0
            eased = ease(tr.easing, p)
            t = start + (end - start) * eased
            states.append(_frame_state(scene, compact, expanded, t))
        # hold at the leg destination
        hold = _frame_state(scene, compact, expanded, end)
        states.extend(hold for _ in range(wait_frames))
    return states
