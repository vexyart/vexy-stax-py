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
from pathlib import Path

from vexy_stax.scene import Scene, View

# Path to the bundled default caption font (issue 328: vexy-stax.ttf == Zalando Sans Expanded,
# the project default; was REM-Regular.ttf in issue 319). The JS engine matches this with the
# Google Font "Zalando Sans" at wdth 125 / wght 500.
_FONTS_DIR = Path(__file__).parent / "fonts"
_DEFAULT_FONT_PATH = _FONTS_DIR / "vexy-stax.ttf"


def default_font_path() -> Path | None:
    """Return the path to the bundled default caption font (vexy-stax.ttf), or None if absent."""
    return _DEFAULT_FONT_PATH if _DEFAULT_FONT_PATH.exists() else None


MIN_GAP = 3.0
FILL = 0.85
V_FILL = 0.98  # expanded: max fraction of frame height the deck may occupy (no crop)

# Caption fade defaults (issue 302 §B.4): captions fade in over the final
# CAPTION_FADE_WINDOW fraction of the morph, staggered back->front by CAPTION_STAGGER.
CAPTION_FADE_WINDOW = 0.9
CAPTION_STAGGER = 0.3
# Caption layout (issue 302 §B, em-based): captions sit to the LEFT of the plates with
# their RIGHT edges aligned CAPTION_GAP_EM em (em == caption size) from the plate left
# edge (0 = touching, issues 321/323), and the text BASELINE CAPTION_BASELINE_EM em above
# the virtual ground (the floor at the bottom of the plates). The nominal "em" is the
# caption size in scene points.
CAPTION_GAP_EM = 0.0  # issues 321/323: caption plate right edge touches slide plate left edge
CAPTION_BASELINE_EM = 1.0
# Caption plate (issues 311, 315): each caption sits on a small white opaque bordered plate.
# The plate height is CAPTION_PLATE_HEIGHT_FRAC of the (frontmost) plate height; the text
# 1em is CAPTION_FONT_FRAC_OF_PLATE of the caption-plate height; the plate is padded by
# CAPTION_PLATE_PAD_EM em on each side of the typeset text. So the default caption size is
# CAPTION_PLATE_HEIGHT_FRAC * CAPTION_FONT_FRAC_OF_PLATE of the scene height. Issue 315 set
# plate height 10%/pad 0.75em; issue 324 makes the default font 1/3 larger (0.075 -> 0.10).
CAPTION_PLATE_HEIGHT_FRAC = 0.1 * 4 / 3  # ≈0.1333 (issue 324: font 1/3 larger; was 0.10)
CAPTION_FONT_FRAC_OF_PLATE = 0.75
CAPTION_PLATE_PAD_EM = 0.75
CAPTION_DEFAULT_SIZE_FRAC = CAPTION_PLATE_HEIGHT_FRAC * CAPTION_FONT_FRAC_OF_PLATE  # ≈0.10 (was 0.075)

# Floor reflection (issue 303 §1) — shared so the blurry reflection is consistent across
# engines. A fraction of the plate-image height (px). (Floor shadows were removed per
# issue 312.)
REFLECTION_BLUR_FRAC = 0.02  # Gaussian blur radius of the mirror reflection (blurry)


def plate_edge_width(scene: Scene) -> float:
    """Plate border thickness in scene points (issue 305): ``edge.width`` × plate height.

    A fraction of the plate height so the border scales with the scene; engines draw a
    frame of this thickness around each plate's rectangle in ``scene.edge.color``. The
    caption plates (issue 311) reuse this same border.
    """
    return scene.size.height * scene.edge.width


def caption_size(scene: Scene) -> float:
    """Nominal caption text size in scene points (1em).

    Resolves ``caption_defaults.size`` when set, else the default of
    ``CAPTION_DEFAULT_SIZE_FRAC`` of the scene height (issue 311: 75% of the caption-plate
    height, which is 20% of the frontmost plate height → 15%). All engines use this one
    nominal size so caption plates and text are sized consistently.
    """
    cd = scene.caption_defaults
    if cd is not None and cd.size is not None:
        return float(cd.size)
    return max(8.0, scene.size.height * CAPTION_DEFAULT_SIZE_FRAC)


def caption_fill_color(scene: Scene) -> str:
    """Caption plate FILL color (issue 324): ``caption_defaults.fill_color`` else the slide
    border color ``scene.edge.color`` (so by default fill, caption border and slide border match)."""
    cd = scene.caption_defaults
    if cd is not None and cd.fill_color:
        return cd.fill_color
    return scene.edge.color


def caption_border_color(scene: Scene) -> str:
    """Caption plate BORDER color (issue 324): ``caption_defaults.border_color`` else
    ``scene.edge.color`` (the slide border color)."""
    cd = scene.caption_defaults
    if cd is not None and cd.border_color:
        return cd.border_color
    return scene.edge.color


def caption_plate_height(scene: Scene) -> float:
    """Height of a caption plate in scene points (issue 311).

    The caption text 1em is ``CAPTION_FONT_FRAC_OF_PLATE`` of this, so the plate height is
    ``caption_size / CAPTION_FONT_FRAC_OF_PLATE`` — keeping the "font = 75% of plate height"
    relationship whether the caption size is the default or explicitly set.
    """
    return caption_size(scene) / CAPTION_FONT_FRAC_OF_PLATE


def caption_plate_center_y(scene: Scene) -> float:
    """World Y of a caption plate's vertical center (issue 311; relayout issue 332).

    The caption plate sits RIGHT ON the floor (its BOTTOM edge on the floor line at
    ``Y = -height/2``), so its center is half its plate height above the ground. The slide
    plate then sits directly on TOP of the caption plate (see :func:`slide_lift`), matching
    the issue 332 stacked layout.
    """
    return -(scene.size.height / 2.0) + caption_plate_height(scene) / 2.0


def slide_lift(scene: Scene) -> float:
    """World Y offset added to EVERY slide plate's vertical center (issue 332).

    With captions ON, each slide plate sits directly on TOP of its caption plate: the slide
    bottom edge == the caption plate top edge. The caption plate stands on the floor and is
    ``caption_plate_height`` tall, so the slide is lifted by exactly one caption-plate height
    relative to the centered (``Y = 0``) convention. With captions OFF there are no caption
    plates and the slide plates sit directly on the floor, so the lift is 0 (slide plate
    center back at ``Y = 0`` — bottom edge on the floor line for the tallest plate).
    """
    return caption_plate_height(scene) if scene.captions else 0.0


def caption_anchor_x(scene: Scene) -> float:
    """World X where every caption plate's LEFT edge aligns (issue 332 relayout).

    Each caption plate is LEFT-aligned with its slide plate: the caption plate left edge
    sits at the slide left edge. All plates share ``scene.size`` width centered at ``X = 0``,
    so the slide (and caption) left edge is ``-width/2``. Engines anchor each caption plate's
    LEFT edge here, just below the slide, at the plate's ``Z``. (``CAPTION_GAP_EM`` is 0, so
    the numeric value is unchanged from the prior right-edge anchor; only the meaning — now a
    LEFT edge — changed for the stacked layout.)
    """
    return -(scene.size.width / 2.0 + CAPTION_GAP_EM * caption_size(scene))


def caption_baseline_y(scene: Scene) -> float:
    """World Y of the caption text BASELINE — 1em above the virtual ground (issue 302 §B).

    The ground is the floor at the bottom of the plates (``Y = -height/2``; the tallest
    plate's vertical middle sits at ``Y = 0``). The baseline is ``CAPTION_BASELINE_EM`` em
    above it, so the captions rest just above the floor on which the plates stand.
    """
    return -(scene.size.height / 2.0) + CAPTION_BASELINE_EM * caption_size(scene)


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
    gaps: list[float]  # effective gap in front of each slide (frontmost slide's gap is unused)
    opacities: list[float]  # per-slide plate opacity
    caption_opacities: list[float]  # per-slide caption opacity (staggered fade)


def plate_gaps(scene: Scene) -> list[float]:
    """Per-slide gap (points). A None field (set only when the scene omits the gap
    key) inherits ``camera.gap``; a 0 field (set by an explicit ``null`` or ``0`` in
    the scene) resolves to the minimal gap (MIN_GAP), as used in the compact view.
    """
    gaps = []
    for s in scene.slides:
        g = scene.camera.gap if s.gap is None else s.gap
        if g == 0.0:
            g = MIN_GAP
        gaps.append(g)
    return gaps


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
    # A slide's gap is the gap IN FRONT of it (between slide i and i+1), so the
    # frontmost slide's gap has no successor and is unused -> sum gaps[:-1].
    return sum(plate_gaps(scene)[:-1])


def _stack_positions(gaps: list[float]) -> list[float]:
    """Per-plate ``Z`` (front plate at 0, index 0 at ``-stack_depth``).

    ``gaps[i]`` is the gap IN FRONT of plate ``i`` (between slide ``i`` and slide
    ``i+1``); the interval before plate ``i`` is therefore ``gaps[i-1]`` and the
    frontmost ``gaps[n-1]`` is unused. Matches the engines' plate placement.
    """
    n = len(gaps)
    if n == 0:
        return []
    depth = sum(gaps[:-1])
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + gaps[i - 1])
    return [c - depth for c in cum]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
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


def expanded_camera(scene: Scene, viewport_aspect: float | None = None) -> CameraPose:
    """Angled hero camera framing the expanded *deck* (SPEC.md §3, issue 302 §2).

    The distance is chosen — and the camera horizontally re-centered (panned) — so
    that, in the projected image, the left margin (viewport edge → leftmost plate)
    and the right margin (rightmost plate → viewport edge) are each equal to the
    *projected gap* between adjacent plates (the mean adjacent plate-center
    horizontal stagger). All plates stay fully inside the frame (a vertical-fit floor
    keeps the deck from cropping top/bottom). Plate size is ``scene.size`` (see module
    docstring) so JS and Python agree exactly; the solve is a deterministic bisection
    so both languages converge identically.

    ``viewport_aspect`` (width/height) defaults to the scene aspect (the rendered
    engines render at ``scene.size``). The live element passes its container aspect so
    the deck fills the viewport vertically when the viewport aspect differs (issue 314).
    """
    cam = scene.camera
    depth = stack_depth(scene, "expanded")
    base_target = (0.0, 0.0, -depth / 2.0)

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

    hfov = math.radians(cam.fov)
    aspect = viewport_aspect if viewport_aspect else scene.size.width / scene.size.height
    vfov = 2.0 * math.atan(math.tan(hfov / 2.0) / aspect)
    th = math.tan(hfov / 2.0)
    tv = math.tan(vfov / 2.0)

    half_w_plate = scene.size.width / 2.0
    half_h_plate = scene.size.height / 2.0
    z_positions = _stack_positions(plate_gaps(scene))

    # Issue 332: slides are LIFTED by one caption-plate height (captions on) so they sit on
    # top of their on-floor caption plates. The full composite the camera must frame (NO crop)
    # spans, vertically, from the floor line (caption-plate bottom == ``-H/2``) up to the
    # lifted slide top (``lift + H/2``). Include the lifted slide corners AND the caption-plate
    # bottom corners so the bounding fit never crops the caption row.
    lift = slide_lift(scene)
    floor_y = -half_h_plate  # caption plate bottom (and floor line) in world Y
    slide_y_lo, slide_y_hi = lift - half_h_plate, lift + half_h_plate
    cap_ys = [floor_y] if scene.captions else []  # extra bottom row (caption plate bottom)

    # Precompute each corner's (right, up, look) components relative to base_target,
    # so projecting at a candidate (distance D, horizontal pan) is cheap and exact.
    # cr/cu/cl: offsets along right/up/look. ndc_x = (cr - pan)/((cl + D)*th).
    corners: list[tuple[float, float, float]] = []
    centers: list[tuple[float, float]] = []  # (right-offset, look-offset) of each plate center
    for z in z_positions:
        rel_c = _sub((0.0, lift, z), base_target)
        centers.append((_dot(rel_c, right), _dot(rel_c, look)))
        for sx in (-half_w_plate, half_w_plate):
            for sy in (slide_y_lo, slide_y_hi, *cap_ys):
                rel = _sub((sx, sy, z), base_target)
                corners.append((_dot(rel, right), _dot(rel, up), _dot(rel, look)))

    def _span(distance: float, pan: float) -> tuple[float, float, float]:
        """Return (min ndc_x, max ndc_x, max |ndc_y|) of the deck at (distance, pan)."""
        a, b, ymax = math.inf, -math.inf, 0.0
        for cr, cu, cl in corners:
            zv = cl + distance
            nx = (cr - pan) / (zv * th)
            a = min(a, nx)
            b = max(b, nx)
            ymax = max(ymax, abs(cu / (zv * tv)))
        return a, b, ymax

    def _gap(distance: float, pan: float) -> float:
        """Mean adjacent plate-center horizontal NDC stagger (the projected gap)."""
        xs = [(cr - pan) / ((cl + distance) * th) for cr, cl in centers]
        if len(xs) < 2:
            return 0.0
        return sum(abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)) / (len(xs) - 1)

    def _recenter(distance: float) -> float:
        """Horizontal pan that centers the projected deck span (so left == right)."""
        lo, hi = -half_w_plate * 8.0, half_w_plate * 8.0
        for _ in range(64):
            pan = 0.5 * (lo + hi)
            a, b, _y = _span(distance, pan)
            if a + b > 0.0:  # span sits right of center -> pan further right
                lo = pan
            else:
                hi = pan
        return 0.5 * (lo + hi)

    # Bracket scale: the legacy bounding-box fit distance.
    half_w = max(abs(cr) for cr, _cu, _cl in corners)
    half_h = max(abs(cu) for _cr, cu, _cl in corners)
    d0 = max(half_w / (FILL * th), half_h / (FILL * tv))

    # margin grows with distance, gap shrinks with distance => (margin - gap) is
    # monotone increasing; bisect for the crossover margin == gap.
    lo, hi = d0 * 0.1, d0 * 20.0
    distance = d0
    for _ in range(80):
        distance = 0.5 * (lo + hi)
        pan = _recenter(distance)
        a, b, _y = _span(distance, pan)
        margin = 0.5 * ((a + 1.0) + (1.0 - b))
        if margin - _gap(distance, pan) > 0.0:
            hi = distance
        else:
            lo = distance
    distance = 0.5 * (lo + hi)

    # Vertical-fit floor: never let the gap pull the camera so close the deck crops
    # top/bottom. Smallest distance whose deck vertical extent fits V_FILL of frame.
    vlo, vhi = d0 * 0.05, d0 * 40.0
    for _ in range(80):
        dv = 0.5 * (vlo + vhi)
        _a, _b, ymax = _span(dv, 0.0)  # vertical extent is independent of pan
        if ymax > V_FILL:
            vlo = dv
        else:
            vhi = dv
    distance = max(distance, 0.5 * (vlo + vhi))

    pan = _recenter(distance)
    near = max(1.0, distance * 0.005)
    target = (
        base_target[0] + right[0] * pan,
        base_target[1] + right[1] * pan,
        base_target[2] + right[2] * pan,
    )
    position = (
        target[0] + to_cam[0] * distance,
        target[1] + to_cam[1] * distance,
        target[2] + to_cam[2] * distance,
    )
    return CameraPose(position=position, target=target, fov=cam.fov, near=near)


def compact_camera(scene: Scene, viewport_aspect: float | None = None) -> CameraPose:
    """Head-on camera on ``+Z`` aimed at the deck center.

    If ``distance`` is a string ending in ``%``, it represents the viewport-fit percentage,
    fitting the frontmost image (width = scene.size.width) so that it occupies P% of the viewport.
    Otherwise, it is treated as absolute points.

    ``viewport_aspect`` (width/height) defaults to the scene aspect — used by the rendered
    engines, which render at ``scene.size``. The live browser element passes its actual
    container aspect so the plate fits tight with aspect-ratio padding when the viewport
    aspect differs from the plate (issue 314: a 2:1 viewport with a narrower plate gets side
    padding, the plate filling the limiting vertical axis).
    """
    cam = scene.camera
    depth = stack_depth(scene, "compact")
    # Issue 337: the compact view frames ONLY the frontmost SLIDE plate — NOT the composite
    # with its caption row. Captions are invisible in the compact view (they fade in only as
    # the deck expands), so reserving the caption-plate height here just padded the frame
    # (bottom, and via the aspect fit, the sides too). The slide plate is lifted by ``lift``
    # (issue 332: it sits on top of the on-floor caption plate), so its center is at ``Y = lift``
    # and it spans height ``H``. Aim at the slide center and fit ``H`` so the slide fills the
    # frame tight with no caption gap. (The expanded view still frames the full composite, where
    # the captions ARE visible.)
    lift = slide_lift(scene)
    target = (0.0, lift, -depth / 2.0)

    is_percent = False
    pct_val = 90.0
    if isinstance(cam.distance, str):
        text = cam.distance.strip()
        if text.endswith("%"):
            is_percent = True
            try:
                pct_val = float(text[:-1])
            except ValueError:
                pct_val = 90.0

    if is_percent:
        # Dual-axis crop-free fit (SPEC.md §3, issue 302 §1, issue 337): fit the frontmost
        # SLIDE plate (width ``W``, height ``H`` — NOT the caption composite) so the *limiting*
        # axis touches P% of the frame and the other axis only ever has extra padding (never a
        # crop). theta_horiz = fov; theta_vert derived from the VIEWPORT aspect; distance =
        # max(d_w, d_h).
        hfov = math.radians(cam.fov)
        aspect = viewport_aspect if viewport_aspect else scene.size.width / scene.size.height
        vfov = 2.0 * math.atan(math.tan(hfov / 2.0) / aspect)
        frac = pct_val / 100.0
        d_w = scene.size.width / (2.0 * math.tan(hfov / 2.0) * frac)
        d_h = scene.size.height / (2.0 * math.tan(vfov / 2.0) * frac)
        dist_to_Z0 = max(d_w, d_h)
        distance = dist_to_Z0 + depth / 2.0
    else:
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
    return float(max(0.0, min(1.0, value)))


def caption_opacities(scene: Scene, t_expanded: float) -> list[float]:
    """Per-slide caption opacity at morph factor ``t_expanded`` (0=compact, 1=expanded).

    Honors ``caption.show_in`` (issue 301 §5) and the staggered fade (issue 302 §B.4):
    an ``expanded`` caption stays invisible until the final ``window`` fraction of the
    morph, then fades in — staggered back (index 0) → front so the frontmost caption
    reaches full opacity exactly at ``t = 1`` (i.e. captions are at full opacity ONLY in
    the expanded view). ``window``/``stagger`` come from ``scene.caption_fade`` (else the
    CAPTION_FADE_WINDOW / CAPTION_STAGGER defaults). ``both`` → 1, ``none`` → 0,
    ``compact`` → fades out linearly as the deck expands. Slides without a caption → 0.
    """
    t = max(0.0, min(1.0, t_expanded))
    # Issue 332: a global captions=false toggle suppresses ALL caption plates everywhere.
    if not scene.captions:
        return [0.0] * len(scene.slides)
    cf = scene.caption_fade
    window = cf.window if cf is not None else CAPTION_FADE_WINDOW
    stagger = cf.stagger if cf is not None else CAPTION_STAGGER
    n = len(scene.slides)
    denom = (n - 1) if n > 1 else 1

    # Total back->front spread (fraction of the morph). Default: `stagger` of the window.
    # Issue 309: if stagger_frames is set + a transition exists, the per-caption step is
    # that many frames of one leg; the spread is (n-1) steps, capped so the frontmost
    # caption still finishes fading at t=1 (ramp stays positive).
    spread = stagger * window
    if cf is not None and cf.stagger_frames is not None and scene.transition is not None:
        leg_frames = round(scene.transition.duration * scene.transition.fps)
        if leg_frames > 0:
            step_t = cf.stagger_frames / leg_frames
            spread = min((n - 1) * step_t, window * 0.95)
    ramp = max(1e-6, window - spread)

    out: list[float] = []
    for i, slide in enumerate(scene.slides):
        cap = slide.caption
        if cap is None or cap.show_in == "none":
            out.append(0.0)
            continue
        if cap.show_in == "both":
            out.append(1.0)
            continue
        if cap.show_in == "compact":
            out.append(1.0 - t)
            continue
        # expanded: staggered window fade-in, backmost (i=0) first, frontmost last.
        start_i = (1.0 - window) + (i / denom) * spread
        out.append(max(0.0, min(1.0, (t - start_i) / ramp)))
    return out


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
    return FrameState(
        camera=_pose_at(scene, compact, expanded, t),
        gaps=gaps,
        opacities=opacities,
        caption_opacities=caption_opacities(scene, t),
    )


# Each transition is a sequence of legs; each leg is (from, to) morph endpoints
# expressed as morph factors (0=compact, 1=expanded). A "wait" hold is inserted
# at the far end of single-direction transitions, between legs for round-trips.
_LEGS: dict[str, list[tuple[float, float]]] = {
    "expand": [(0.0, 1.0)],
    "collapse": [(1.0, 0.0)],
    "expand_collapse": [(0.0, 1.0), (1.0, 0.0)],
    "collapse_expand": [(1.0, 0.0), (0.0, 1.0)],
}


def video_fps(scene: Scene) -> int:
    """Resolve the video frame rate (issue 335 §3).

    Precedence: ``scene.video.fps`` when set (it overrides for VIDEO rendering), else the legacy
    ``scene.transition.fps`` (so an unmodified scene keeps its prior frame rate), else 30. All
    engines read this for the encoder frame rate so the held stills and the transition play back
    at one consistent rate.
    """
    if scene.video.fps is not None:
        return scene.video.fps
    if scene.transition is not None:
        return scene.transition.fps
    return 30


def video_dimensions(scene: Scene) -> tuple[int, int]:
    """Resolve the video (width, height) (issue 335 §3): ``scene.video`` else ``scene.size``."""
    v = scene.video
    width = v.width if v.width is not None else scene.size.width
    height = v.height if v.height is not None else scene.size.height
    return width, height


def transition_frames(scene: Scene) -> int:
    """Resolve the number of TRANSITION frames per leg (issue 335 §3).

    ``scene.video.frames`` is authoritative when set; otherwise it falls back to the legacy
    ``round(transition.duration * video.fps)`` so the default preserves prior behavior. Zero
    when there is no transition.
    """
    tr = scene.transition
    if tr is None:
        return 0
    if scene.video.frames is not None:
        return scene.video.frames
    return round(tr.duration * video_fps(scene))


def frame_plan(
    scene: Scene,
    first_hold: int | None = None,
    last_hold: int | None = None,
) -> list[FrameState]:
    """Per-frame states for ``scene.transition`` (empty when no transition).

    Layout (issue 335 §2/§3): the transition itself renders ``transition_frames`` frames per
    leg (``scene.video.frames`` when set, else ``round(duration*video.fps)``); a hold of
    ``round(wait*video.fps)`` frames is inserted at the far end of each leg. The whole clip is
    then bookended with HELD STILLS — ``first_hold`` copies of the FIRST FrameState prepended
    and ``last_hold`` copies of the LAST FrameState appended (still → transition → still). The
    holds default to ``scene.video.first_hold`` / ``scene.video.last_hold`` (10 each); pass
    explicit ints to override per call. Held frames are exact copies of the boundary states, so
    every engine (which simply consumes this list) keyframes the repeats correctly.

    Total length: ``first_hold + legs * (transition_frames + round(wait*fps)) + last_hold``.
    """
    tr = scene.transition
    if tr is None:
        return []
    fh = scene.video.first_hold if first_hold is None else first_hold
    lh = scene.video.last_hold if last_hold is None else last_hold
    compact = compact_camera(scene)
    expanded = expanded_camera(scene)
    fps = video_fps(scene)
    leg_frames = transition_frames(scene)
    wait_frames = round(tr.wait * fps)
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

    # Issue 335 §2: bookend with held stills — repeat the first/last FrameState so the clip
    # opens and closes on a still image (default 10 frames each, default-on). Empty plans
    # (no leg/wait frames) get no holds: there is nothing to hold.
    if not states:
        return states
    head = [states[0]] * max(0, fh)
    tail = [states[-1]] * max(0, lh)
    return head + states + tail
