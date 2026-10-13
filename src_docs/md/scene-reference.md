# Scene reference

Field-by-field reference for scene format version 1. The defaults below are the defaults of the Pydantic model in `src/vexy_stax/scene.py`, which mirrors `schema/vexy-stax-scene.schema.json`.

## `version`

Integer, must be `1`. The schema requires it; the Python model fills in `1` when it is missing.

## `view`

`"expanded"` (default) or `"compact"`. The initial view of the scene. The CLI `render` command takes its view from `--view`, not from this field.

## `size`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `width` | integer ≥ 1 | `1920` | Output width in pixels. |
| `height` | integer ≥ 1 | `1080` | Output height in pixels. |

The size is also the nominal plate size used for camera framing, so Python and JS frame identically.

## `camera`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `gap` | number ≥ 0 | `1920` | Points between adjacent plates in the expanded view. `0` resolves to `MIN_GAP` (3.0). |
| `distance` | number or string | `"100%"` | Compact-view camera distance. See below. |
| `angle` | number | `60` | Expanded-camera azimuth in degrees. `0` is head-on; positive values swing the camera toward `-X`. |
| `elevation` | number | `0` | Expanded-camera elevation in degrees above the horizon. |
| `fov` | number, 0 < fov < 180 | `39.6` | Horizontal field of view in degrees. |

`distance` takes two forms:

- **A percentage string** such as `"100%"` or `"90%"`. The frontmost slide plate is fitted so that the limiting axis fills that percentage of the frame; the other axis only gains padding, never crops. `"90%"` leaves 10 % padding on the limiting axis.
- **A number** or numeric string such as `2000` or `"2000"`: an absolute distance in points.

The expanded camera ignores `distance`; its distance comes from the framing solve (see [Geometry](geometry.md)).

## `transition`

Optional. Omit it for still-only scenes. Video rendering requires it.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `kind` | string | — (required) | `expand`, `collapse`, `expand_collapse` or `collapse_expand`. |
| `duration` | number > 0 | `3.0` | Seconds per leg. |
| `wait` | number ≥ 0 | `1.0` | Seconds to hold at the end of each leg. |
| `fps` | integer ≥ 1 | `30` | Frame rate, unless `video.fps` overrides it. |
| `easing` | string | `"easeInOutCubic"` | `linear`, `easeInOutCubic`, `easeOutCubic` or `easeInCubic`. |

## `video`

Output settings for video rendering. `transition` defines the animation; `video` defines the output.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `width` | integer ≥ 1 or null | `null` → `size.width` | Video width. |
| `height` | integer ≥ 1 or null | `null` → `size.height` | Video height. |
| `fps` | integer ≥ 1 or null | `null` → `transition.fps`, else 30 | Frame rate. Overrides `transition.fps` when set. |
| `frames` | integer ≥ 1 or null | `null` → `round(duration × fps)` | Transition frames **per leg**. |
| `first_hold` | integer ≥ 0 | `10` | Copies of the first frame added at the start. |
| `last_hold` | integer ≥ 0 | `10` | Copies of the last frame added at the end. |

Total frame count:

```text
total = first_hold + legs × (frames + round(wait × fps)) + last_hold
```

For `expand_collapse` with `duration` 3.0, `wait` 1.0 and 30 fps: `10 + 2 × (90 + 30) + 10 = 260` frames.

All six values can be overridden per render with the `video` command flags (`--width`, `--height`, `--fps`, `--frames`, `--first_hold`, `--last_hold`). The Blender engine additionally caps video at 1920 pixels on the long edge.

## `floor`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `color` | string | `"#ffffff"` | Tint of the floor pane. |
| `opacity` | number 0–1 | `0.0` | Opacity of the floor pane. `0` hides the pane. |
| `reflectivity` | number 0–1 | `0.1` | Strength of the blurred plate reflection. `0` turns it off. |

`dir2scene` writes different values: `color` `#f2f2f2`, `opacity` 1.0, `reflectivity` 0.5 (changeable with its `--floor_*` flags).

## `edge`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `width` | number ≥ 0 | `0.0` | Border thickness as a fraction of the scene height. `0` turns borders off on slide and caption plates. |
| `color` | string | `"#f2f2f2"` | Border colour. Also the default caption-plate fill and border colour. |

For a 1080-pixel-high scene, `width: 0.004` gives a border of about 4.3 points.

## `background`

Background colour as a hex string. Default `"#ffffff"`.

## `juicy`

Boolean, default `false`. Marks a scene for per-channel colour matching between the 3D render and the flat Pillow overlay. The matching functions live in `vexy_stax.juicy` (see [Python API](python-api.md#vexy_staxjuicy)); the `render` and `video` commands don't apply them. vexy-stax-js ignores this field.

## `captions`

Boolean, default `true`. With `true`, caption plates are drawn and slide plates are lifted to sit on top of them. With `false`, no caption plates are drawn at all and slides stand on the floor.

## `caption_defaults`

Default caption style, used by every caption that doesn't override a field in its own `style`.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `size` | number > 0 or null | `null` | Caption text size (1 em) in points. `null` → 10 % of the scene height, at least 8 points. |
| `color` | string or null | `null` | Text colour. Engines fall back to `#222222`. |
| `font` | string or null | `null` | Font. `null` → the bundled `vexy-stax.ttf`. A path to a font file works in every engine. The Blender engine replaces anything else with the bundled font; pygfx passes other family names to its font manager. |
| `fill_color` | string or null | `null` | Caption-plate fill. `null` → `edge.color`. |
| `border_color` | string or null | `null` | Caption-plate border. `null` → `edge.color`. |

## `caption_fade`

Timing of the caption fade-in during a transition. When omitted, `window` 0.9 and `stagger` 0.3 apply.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `window` | number, 0 < w ≤ 1 | `0.9` | Fraction of the morph, counted back from the expanded end, during which captions fade in. |
| `stagger` | number, 0 ≤ s < 1 | `0.3` | Back-to-front spread of the fade starts, as a fraction of `window`. |
| `stagger_frames` | integer ≥ 0 or null | `null` | Step between captions in transition frames. Overrides `stagger` when set. |

See [Captions](captions.md#fade-timing) for the exact formula.

## `slides`

An array of at least one slide, ordered back to front.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `src` | string | — (required) | Image path relative to the scene file, an absolute path, or a `data:` URI. |
| `gap` | number ≥ 0 or null | key omitted | Expanded-view gap for this slide. See below. |
| `opacity` | number or object | `1.0` | Plate opacity: one number, or `{ "expanded": x, "compact": y }`. |
| `caption` | object or null | `null` | The slide's caption. |

### Per-slide `gap` has three states

| In the file | Effect |
|-------------|--------|
| key omitted | inherits `camera.gap` |
| `"gap": 400` | uses 400 points |
| `"gap": null` or `"gap": 0` | uses `MIN_GAP` (3.0), the compact spacing |

!!! note
    `dir2scene` writes `"gap": null` for every slide, which collapses the expanded view. Remove those keys after generating a scene.

### `caption`

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `text` | string | — (required) | The caption text. |
| `show_in` | string | `"expanded"` | `expanded`, `compact`, `both` or `none`. |
| `style` | object or null | `null` | Per-caption overrides; same fields as `caption_defaults`. |
