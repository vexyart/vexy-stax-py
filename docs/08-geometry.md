---
title: View Geometry & Framing
nav_order: 9
---

# View Geometry & Framing

All camera math lives in `src/vexy_stax/geometry.py` (Python) and is mirrored identically in `vexy-stax-js/src/geometry.js`. Both implementations are tested against the same fixture vectors, so the four renderers produce numerically identical frame states.

---

## Coordinate system

```
        +Y (up)
        |
        |     +Z (toward viewer)
        |    /
        |   /
        |  /
        | /
        +------------- +X (right)
       /|
      / |
    -Z  -Y
```

| Axis | Meaning |
|------|---------|
| `X` | Plate width; plates centered at `X = 0` |
| `Y` | Vertical (up); plate centers at `Y = 0`; floor at `Y = -height/2` |
| `Z` | Depth; front plate at `Z = 0`; `+Z` toward the viewer |

All plates share the scene coordinate frame. The deck center along `Z` is at `Z = -stack_depth / 2`.

---

## Stack depth and plate positions

```python
def stack_depth(scene: Scene, view: View) -> float:
    # compact: (N-1) × MIN_GAP  (MIN_GAP = 3 pt)
    # expanded: sum of per-slide gaps[1:]
    ...

def plate_gaps(scene: Scene) -> list[float]:
    # Falls back to camera.gap for slides with gap=None
    ...
```

Plate `Z` positions are computed cumulatively from the back:

- Plate `N-1` (frontmost): `Z = 0`
- Plate `N-2`: `Z = -gap[N-1]`
- Plate `0` (backmost): `Z = -stack_depth`

The deck center sits at `Z = -stack_depth / 2`.

---

## Compact camera

The compact camera sits head-on on `+Z`, aimed directly at the deck center:

```
position = (0, 0, target_z + distance)
target   = (0, 0, -stack_depth/2)
```

### Distance resolution

`camera.distance` can be:

- An **absolute number** (or numeric string): used directly.
- A **`"P%"` string**: dual-axis crop-free fit. The frontmost plate (`Z = 0`, size `scene.size`) is fit so the *limiting* axis touches `P%` of the frame and the other axis only ever has extra padding — never a crop:

```
hfov = camera.fov (horizontal)
vfov = 2 · arctan(tan(hfov/2) / aspect)

d_w = scene.size.width  / (2 · tan(hfov/2) · (P/100))
d_h = scene.size.height / (2 · tan(vfov/2) · (P/100))
d_fit = max(d_w, d_h)          # limiting axis touches P%
distance = d_fit + stack_depth/2
```

`"100%"` (the default) fits the limiting axis exactly to the frame edge. `"90%"` leaves 10% padding on the limiting axis.

### Near plane

```
near = max(1.0, distance × 0.005)
```

This prevents depth-buffer flashing when the camera is very close.

---

## Expanded camera

The expanded camera orbits to an azimuth/elevation position and is automatically framed so that:

1. The projected left margin equals the projected right margin (the deck is horizontally centered).
2. Each margin equals the mean projected gap between adjacent plate centers.
3. The deck never crops top or bottom (`V_FILL = 0.98`).

### Direction computation

```python
az = radians(camera.angle)
el = radians(camera.elevation)

to_cam = normalize(
    -sin(az) · cos(el),   # X: swing toward -X as az increases
     sin(el),              # Y: lift with elevation
     cos(az) · cos(el),   # Z: head-on at az=0
)
```

### Distance and pan solve (bisection)

The engine simultaneously solves for:

- **`distance`**: the camera distance from the deck center.
- **`pan`**: a horizontal offset along the camera's `right` axis.

**Re-centering pan** (`_recenter`): for a given distance, bisect for the pan that makes `span_min + span_max = 0` (left NDC extent equals negative of right NDC extent). Converges in 64 iterations.

**Distance bisect**: margin grows with distance, projected gap shrinks with distance — so `margin − gap` is monotone increasing. Bisect for `margin == gap`. Converges in 80 iterations.

**Vertical floor check**: after finding the margin-gap distance, compute the smallest distance at which the deck's vertical extent stays within `V_FILL = 0.98` of the frame. Take `max(margin_distance, vertical_distance)`.

The final camera position is:

```python
target   = base_target + right × pan
position = target + to_cam × distance
```

### Why bisection instead of a closed form?

The angled deck projects asymmetrically onto the image plane. The projected gap and margins have no clean closed-form solution when the camera is panned. Bisection is deterministic and converges identically in Python and JS with the same iteration counts, ensuring pixel-exact parity.

---

## Transition interpolation

Frame states for a transition are computed by `frame_plan(scene)`:

```python
@dataclass
class FrameState:
    camera: CameraPose           # interpolated camera
    gaps: list[float]            # per-slide gap (lerped MIN_GAP → camera.gap)
    opacities: list[float]       # per-slide plate opacity
    caption_opacities: list[float]  # per-slide caption opacity
```

For each frame at eased morph factor `t` (0 = compact, 1 = expanded):

```python
gaps[i]      = MIN_GAP + (expanded_gap[i] - MIN_GAP) × t
opacities[i] = lerp(slide.opacity.compact, slide.opacity.expanded, t)
camera       = lerp(compact_pose, expanded_pose, t)
```

The easing is applied to raw progress `p ∈ [0,1)` across the leg:

```python
p = i / leg_frames
t = ease(transition.easing, p)   # e.g. easeInOutCubic
morph = start + (end - start) × t
```

### Held first/last still frames (issue 335 §2)

`frame_plan` bookends the transition with **held stills**: it prepends `scene.video.first_hold`
copies of the first `FrameState` and appends `scene.video.last_hold` copies of the last
(default 10 each, default-on), so a rendered video plays `still(N) → transition → still(N)`.
The per-leg transition frame count and the encoder fps are resolved from the
[`video`](04-scene-format-reference.md#video) section:

```python
g.video_fps(scene)          # video.fps, else transition.fps, else 30
g.video_dimensions(scene)   # (video.width|size.width, video.height|size.height)
g.transition_frames(scene)  # video.frames, else round(duration × video_fps)

# Holds default to scene.video.first_hold/last_hold; override per call:
states = g.frame_plan(scene, first_hold=0, last_hold=0)   # holds disabled
```

Total length: `first_hold + legs × (transition_frames + round(wait × fps)) + last_hold`.

---

## Easing curves

```python
def ease(name: str, t: float) -> float:
    t = clamp(t, 0, 1)
    if name == "linear":
        return t
    if name == "easeInCubic":
        return t³
    if name == "easeOutCubic":
        return 1 - (1-t)³
    if name == "easeInOutCubic":
        if t < 0.5: return 4t³
        else:       return 1 - (-2t+2)³ / 2
```

All four curves are evaluated identically in `geometry.py` and `geometry.js`. The Blender engine maps them to equivalent Bezier handles for Blender's animation system.

**Tip**: `easeInOutCubic` concentrates motion in the middle and can make the camera appear to stop near the endpoints on wide-gap decks. Use `"linear"` for continuous, uniform-speed animations.

---

## Key constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MIN_GAP` | `3.0` | Minimum plate separation in compact view (pt) |
| `FILL` | `0.85` | Bracket fraction for expanded camera bisect |
| `V_FILL` | `0.98` | Max vertical fraction the deck may occupy |
| `REFLECTION_BLUR_FRAC` | `0.02` | Blur radius as fraction of plate height |

---

## Public API summary

```python
from vexy_stax import geometry as g

# Camera poses
pose = g.compact_camera(scene)           # CameraPose
pose = g.expanded_camera(scene)          # CameraPose

# Plate layout
gaps   = g.plate_gaps(scene)             # list[float]
depth  = g.stack_depth(scene, "expanded")

# Caption geometry
size   = g.caption_size(scene)           # 1em in world points
x      = g.caption_anchor_x(scene)      # right edge X of all captions
y      = g.caption_plate_center_y(scene) # center Y of caption plates
by     = g.caption_baseline_y(scene)    # text baseline Y
w      = g.plate_edge_width(scene)      # border thickness in points

# Transition
states = g.frame_plan(scene)            # list[FrameState]
opacs  = g.caption_opacities(scene, t)  # list[float] at morph t

# Easing
v = g.ease("easeInOutCubic", 0.5)       # 0.5
```
