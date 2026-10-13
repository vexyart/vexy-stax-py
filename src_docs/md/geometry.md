# Geometry

All view math lives in `src/vexy_stax/geometry.py`. The module is pure: it uses math and the standard library, holds no rendering code, and returns plain values and frozen dataclasses. All three Python engines use it, and vexy-stax-js mirrors it in `geometry.js`. The repository's `SPEC.md` (section 3) is the normative description.

The examples on this page use a default scene with three captioned slides and an `expand` transition: `size` 1920 × 1080, `camera.gap` 1920, `angle` 60, `elevation` 0, `fov` 39.6, `distance` `"100%"`.

## Data types

```python
@dataclass(frozen=True)
class CameraPose:
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float   # degrees, horizontal
    near: float  # near clipping plane

@dataclass(frozen=True)
class FrameState:
    camera: CameraPose
    gaps: list[float]               # per-slide gap
    opacities: list[float]          # per-slide plate opacity
    caption_opacities: list[float]  # per-slide caption opacity
```

## Gaps and stack depth

`plate_gaps(scene)` returns one gap per slide: the slide's own `gap`, or `camera.gap` when the slide omits the key, with `0` replaced by `MIN_GAP` (3.0).

`stack_depth(scene, view)` is the sum of the gaps between adjacent plates:

- `"compact"`: `(N − 1) × MIN_GAP`. Three slides give `6.0`.
- `"expanded"`: the sum of the per-slide gaps. Three slides with gap 1920 give `3840.0`.

The front plate sits at `Z = 0`, slide 0 at `Z = −stack_depth`, and the deck centre at `Z = −stack_depth / 2`.

## Slide lift

With captions on, `slide_lift(scene)` returns one caption-plate height (144 points in the example), and every slide plate centre moves up by that amount so the slide sits on its caption plate. With `captions: false` the lift is 0.

## Compact camera

`compact_camera(scene, viewport_aspect=None)` puts the camera on the `+Z` axis, aimed at the centre of the frontmost slide plate:

```text
target   = (0, lift, −stack_depth/2)
position = target + (0, 0, distance)
near     = max(1.0, distance × 0.005)
```

For a percentage `distance` such as `"100%"`, the frontmost slide plate (`scene.size`) is fitted so the limiting axis fills P % of the frame:

```text
hfov  = camera.fov
vfov  = 2 · atan(tan(hfov/2) / aspect)
d_w   = width  / (2 · tan(hfov/2) · P/100)
d_h   = height / (2 · tan(vfov/2) · P/100)
distance = max(d_w, d_h) + stack_depth/2
```

`aspect` is `viewport_aspect` when given, otherwise `width / height`. A numeric `distance` is used as is.

In the example: `target = (0, 144, −3)`, `position ≈ (0, 144, 2666.5)`, `near ≈ 13.3`.

## Expanded camera

`expanded_camera(scene, viewport_aspect=None)` orbits the camera around the deck centre. The direction from target to camera is

```text
to_cam = normalize(−sin(az)·cos(el),  sin(el),  cos(az)·cos(el))
```

with `az = angle` and `el = elevation` in radians. `az = 0` is head-on; positive angles swing toward `−X`.

The distance and a horizontal pan are then solved so that, in the projected image:

1. the deck is centred: the left margin equals the right margin,
2. each margin equals the mean projected horizontal distance between adjacent plate centres,
3. the deck's vertical extent fits within `V_FILL = 0.98` of the frame height, so nothing crops at the top or bottom. The bounds include the lifted slides and, with captions on, the caption row on the floor.

The solve uses bisection. Re-centring the pan runs 64 iterations; the margin-equals-gap distance and the vertical-fit distance run 80 iterations each, and the camera uses the larger of the two distances. The initial bracket comes from a bounding-box fit at `FILL = 0.85`. Bisection is deterministic, so Python and JavaScript converge to the same pose.

In the example the expanded camera lands at `position ≈ (−9168.5, 0, 3403.5)`, looking at `target ≈ (13.0, 0, −1897.5)`.

## Transition frames

`frame_plan(scene, first_hold=None, last_hold=None)` returns the list of `FrameState` objects for the scene's transition, or `[]` without one.

For each leg, for frame `i` of `leg_frames`:

```text
p = i / leg_frames          # 0 ≤ p < 1
t = start + (end − start) · ease(easing, p)
```

`t` is the morph factor (0 = compact, 1 = expanded). The frame state at `t` is

```text
gaps[i]      = MIN_GAP + (expanded_gap[i] − MIN_GAP) · t
opacities[i] = compact_opacity + (expanded_opacity − compact_opacity) · t
camera       = linear interpolation of position, target, fov and near
caption_opacities = caption_opacities(scene, t)
```

After each leg, `round(wait × fps)` copies of the end state are appended. Finally the whole list is bookended with `first_hold` copies of the first state and `last_hold` copies of the last; both default to the scene's `video.first_hold` and `video.last_hold`.

Related helpers:

| Function | Returns |
|----------|---------|
| `video_fps(scene)` | `video.fps`, else `transition.fps`, else 30 |
| `video_dimensions(scene)` | `(video.width or size.width, video.height or size.height)` |
| `transition_frames(scene)` | `video.frames`, else `round(duration × video_fps)`; 0 without a transition |

For the example `expand` transition: `transition_frames` is 90, the wait adds 30, and the holds add 20, so `len(frame_plan(scene)) == 140`.

## Easing

`ease(name, t)` clamps `t` to `[0, 1]` and evaluates `linear`, `easeInCubic`, `easeOutCubic` or `easeInOutCubic`. Any other name raises `ValueError`. For example `ease("easeOutCubic", 0.8)` returns `0.992`.

## Opacity

`interpolate_opacity(slide, t_expanded)` interpolates between the slide's compact and expanded opacity and clamps the result to `[0, 1]`.

## Constants

| Constant | Value | Use |
|----------|-------|-----|
| `MIN_GAP` | `3.0` | Compact spacing; replaces a zero gap. |
| `FILL` | `0.85` | Bracket for the expanded distance solve. |
| `V_FILL` | `0.98` | Maximum vertical fraction of the frame the expanded deck may fill. |
| `REFLECTION_BLUR_FRAC` | `0.02` | Reflection blur radius as a fraction of the plate height. |
| `CAPTION_FADE_WINDOW` | `0.9` | Default `caption_fade.window`. |
| `CAPTION_STAGGER` | `0.3` | Default `caption_fade.stagger`. |
| `CAPTION_PLATE_HEIGHT_FRAC` | `0.1 × 4/3` ≈ 0.1333 | Default caption-plate height as a fraction of the scene height. |
| `CAPTION_FONT_FRAC_OF_PLATE` | `0.75` | Text size as a fraction of the caption-plate height. |
| `CAPTION_PLATE_PAD_EM` | `0.75` | Horizontal padding on each side of the caption text, in em. |
| `CAPTION_BASELINE_EM` | `1.0` | Text baseline height above the floor, in em. |
| `CAPTION_GAP_EM` | `0.0` | Horizontal offset of the caption anchor, in em. |
