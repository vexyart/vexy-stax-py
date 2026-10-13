# Concepts

## Scene

A **scene** is an ordered list of **slides** plus settings for the camera, the floor, plate borders, captions, the transition and video output. It lives in one JSON document that vexy-stax-py and vexy-stax-js both read. See [Scene format](scene-format.md).

## Slides and plates

Each slide is one image, drawn as a flat upright **plate** in 3D space. A plate's width and height in world units ("points") equal the pixel size of its image.

Slides are ordered **back to front**: index `0` is the farthest plate, the last slide is the closest. In the sample deck `testdata/airbl-lores/`, `airbl-010-back.png` is slide 0 and `airbl-090-ui.png` is the frontmost.

## The deck

The **deck** is the stack of plates along the `Z` axis:

- the frontmost plate sits at `Z = 0`,
- each plate behind it sits further along `-Z`, separated by its **gap**,
- slide 0 sits at `Z = -stack_depth`, where `stack_depth` is the sum of the gaps between adjacent plates.

## Coordinate system

vexy-stax uses a right-handed, Y-up frame, the same one three.js uses. The Blender render script, the pygfx engine and the JS stage all build their scenes in it, so camera poses can be exchanged between renderers.

| Axis | Meaning |
|------|---------|
| `X` | Plate width. Plates are centred on `X = 0`. |
| `Y` | Up. The floor line is `Y = -height/2`. |
| `Z` | Depth. The front plate is at `Z = 0`; `+Z` points toward the viewer. |

The camera framing is computed from `scene.size`, so all engines frame the deck the same way even if individual images differ in size.

## Two views

### Expanded

- The camera orbits around the deck centre by `camera.angle` (azimuth) and `camera.elevation`.
- Plates are spaced by their gaps (`camera.gap`, or a per-slide `gap`).
- Captions with `show_in: "expanded"` are visible.
- The framing is solved automatically: the deck is centred horizontally, the left and right margins each equal the projected spacing between adjacent plates, and the deck never crops at the top or bottom.

### Compact

- The camera sits head-on on the `+Z` axis, aimed at the deck centre.
- Every gap collapses to `MIN_GAP = 3.0` points, just enough to keep plates from z-fighting.
- The frontmost slide plate is fitted to the frame according to `camera.distance` (for example `"100%"`).
- Captions with `show_in: "expanded"` are hidden.

## Transitions

A **transition** animates between the two views. It is made of one or two **legs**:

| `kind` | Legs |
|--------|------|
| `expand` | compact → expanded |
| `collapse` | expanded → compact |
| `expand_collapse` | compact → expanded, then expanded → compact |
| `collapse_expand` | expanded → compact, then compact → expanded |

Each leg lasts `duration` seconds. After each leg the view holds still for `wait` seconds. During a leg, a morph factor `t` runs from 0 (compact) to 1 (expanded), or back, shaped by the `easing` curve. At each frame vexy-stax interpolates:

1. the camera position, target, field of view and near plane (linear interpolation between the compact and expanded poses),
2. every gap, from `MIN_GAP` to its expanded value,
3. every slide's opacity, from its compact to its expanded value,
4. every caption's opacity, with the staggered fade described in [Captions](captions.md).

Video output also holds the first and last frame for a number of frames (10 each by default), so a clip opens and closes on a still image.

## Easing

Four named curves are available. All interpolation in a leg uses the same curve.

| Name | Shape |
|------|-------|
| `linear` | `t` |
| `easeInCubic` | `t³`: slow start, fast finish |
| `easeOutCubic` | `1 − (1 − t)³`: fast start, slow finish |
| `easeInOutCubic` | `4t³` below 0.5, `1 − (−2t + 2)³ / 2` above: the default |

`easeInOutCubic` concentrates motion in the middle of the leg. Use `linear` for constant-speed motion.

## Opacity

A slide's `opacity` is either one number (`0.8`, used in both views) or a per-view object such as `{ "expanded": 1.0, "compact": 0.4 }`. The per-view form is interpolated with the same easing as the camera. `"compact": 0` hides a slide in the compact view while keeping it in the expanded view. Values are clamped to `[0, 1]`.

## The floor

The **floor** is a horizontal plane at the bottom of the deck. It has two parts:

- a pane, tinted with `floor.color` at `floor.opacity`,
- a blurred reflection of the plates, scaled by `floor.reflectivity`. The blur radius is `REFLECTION_BLUR_FRAC = 0.02` of the plate height, so the reflection reads as soft rather than mirror-sharp.

By default the pane is invisible (`opacity` 0.0) and the reflection is faint (`reflectivity` 0.1). Raise `opacity` for a visible floor.

## Captions and the stacked layout

A **caption** is a text label for one slide, drawn as a small opaque plate with the text on it. With captions on (`captions: true`, the default):

- each caption plate stands on the floor, at its slide's depth, left-aligned with the slide plate;
- each slide plate is lifted by one caption-plate height so it sits on top of its caption plate.

With `captions: false` no caption plates are drawn and the slides stand directly on the floor. See [Captions](captions.md) for sizes, colours and fade timing.

## Plate borders

`edge.width` draws a frame around every slide plate and caption plate. It is a fraction of the scene height and is `0` (off) by default. `edge.color` sets the border colour and is also the default fill and border colour of caption plates.
