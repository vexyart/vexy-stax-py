---
title: Scene Format Reference
nav_order: 5
---

# Scene Format Reference

Full field-by-field documentation for scene format v1. All defaults match the JSON Schema at `schema/vexy-stax-scene.schema.json` and the Pydantic model in `src/vexy_stax/scene.py`.

---

## `version`

```json
"version": 1
```

**Required.** Must be exactly `1`. Unknown versions are rejected.

---

## `view`

```json
"view": "expanded"
```

**Optional.** Default: `"expanded"`.

The initial view for still renders and the starting state for the browser component.

- `"expanded"` — angled camera, plates spaced, captions on.
- `"compact"` — head-on camera, plates collapsed to `MIN_GAP`.

---

## `size`

```json
"size": { "width": 1920, "height": 1080 }
```

**Optional.** Default: `{ "width": 1920, "height": 1080 }`.

Canvas dimensions in pixels. These also serve as the nominal plate dimensions for camera framing so Python and JS agree exactly. Both values must be ≥ 1.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | integer | `1920` | Canvas width in pixels |
| `height` | integer | `1080` | Canvas height in pixels |

---

## `camera`

```json
"camera": {
  "gap": 1920,
  "distance": "100%",
  "angle": 60,
  "elevation": 0,
  "fov": 39.6
}
```

**Optional.** All sub-fields have defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `gap` | number ≥ 0 | `1920` | Points between adjacent plates in the expanded view. Also the default per-slide gap. |
| `distance` | number or string | `"100%"` | Camera distance. A number or numeric string is absolute points. A `"P%"` string fits the frontmost plate so the limiting axis occupies `P%` of the viewport (dual-axis crop-free). |
| `angle` | number | `60` | Azimuth degrees for the expanded camera. `0` = head-on (`+Z`); positive values swing toward `-X` (left-side view). |
| `elevation` | number | `0` | Degrees above the horizon for the expanded camera. `0` = horizon level; positive lifts the camera up. |
| `fov` | number | `39.6` | Horizontal field of view in degrees. `39.6°` approximates a 50 mm lens. Must be in `(0, 180)`. |

**Distance spec examples:**

```json
"distance": "100%"   // limiting axis exactly fills the frame
"distance": "90%"    // 10% padding on the limiting axis
"distance": 2000     // absolute 2000 points
"distance": "2000"   // same, as a string
```

---

## `transition`

```json
"transition": {
  "kind": "expand_collapse",
  "duration": 3.0,
  "wait": 1.0,
  "fps": 30,
  "easing": "easeInOutCubic"
}
```

**Optional.** Omit this block entirely for still-only scenes (no video output). When present, `kind` is required.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kind` | string | — | **Required.** One of `"expand"`, `"collapse"`, `"expand_collapse"`, `"collapse_expand"`. |
| `duration` | number > 0 | `3.0` | Seconds per leg of the animation. |
| `wait` | number ≥ 0 | `1.0` | Hold time in seconds at the far end of each leg before returning. |
| `fps` | integer ≥ 1 | `30` | Frames per second. |
| `easing` | string | `"easeInOutCubic"` | Easing curve name. One of `"linear"`, `"easeInOutCubic"`, `"easeOutCubic"`, `"easeInCubic"`. |

**Transition kinds:**

| `kind` | Motion |
|--------|--------|
| `expand` | compact → expanded |
| `collapse` | expanded → compact |
| `expand_collapse` | compact → expanded → compact (round-trip) |
| `collapse_expand` | expanded → compact → expanded (round-trip) |

For round-trip transitions, the `wait` hold fires at the midpoint (the far view) between the two legs.

**Frame count formula** (transition body, before held stills):

```
transition_frames = legs × (frames_per_leg + round(wait × fps))
```

where `frames_per_leg` defaults to `round(duration × fps)` but is overridable via the
[`video`](#video) section, and `fps` defaults to `transition.fps` (overridable via
`video.fps`). For `expand_collapse` with `duration=3.0`, `wait=1.0`, `fps=30`:
`2 × (90 + 30) = 240` transition frames = 8 s. The rendered **video** additionally bookends
this with held first/last stills — see [`video`](#video).

> The `fps` here is the legacy transition rate. For **video** output the `video` section
> takes precedence (`video.fps` overrides it); `transition.fps` remains the fallback.

---

## `video`

```json
"video": {
  "width": null,
  "height": null,
  "fps": null,
  "frames": null,
  "first_hold": 10,
  "last_hold": 10
}
```

**Optional** (issue 335). Centralizes the parameters used when an engine renders a transition
**video**, keeping them separate from the [`transition`](#transition) animation definition.
Always present with defaults that preserve prior behavior, so you only set the fields you want
to change.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | integer ≥ 1 / null | `size.width` | Video pixel width; `null` ⇒ the scene size. |
| `height` | integer ≥ 1 / null | `size.height` | Video pixel height; `null` ⇒ the scene size. |
| `fps` | integer ≥ 1 / null | `transition.fps` (else `30`) | Encoded frame rate. **Overrides** `transition.fps` for video when set. |
| `frames` | integer ≥ 1 / null | `round(duration × fps)` | Number of TRANSITION frames **per leg**. |
| `first_hold` | integer ≥ 0 | `10` | Held copies of the FIRST frame — a still **intro**. |
| `last_hold` | integer ≥ 0 | `10` | Held copies of the LAST frame — a still **outro**. |

**Held still frames (default-on).** Every transition video holds its first frame for
`first_hold` frames and its last frame for `last_hold` frames: `still(N) → transition →
still(N)`. The holds are exact copies of the boundary frames, so the clip opens and closes on
a steady image. Set either count to `0` to disable that hold.

**Total rendered length:**

```
total = first_hold + legs × (frames + round(wait × fps)) + last_hold
```

**Precedence vs `transition`.** `transition` owns the animation (`kind`/`easing`/`wait`/
`duration`); `video` owns the output framing. `video.fps`/`frames`/`width`/`height` win when
set, otherwise each falls back to the legacy `transition`/`size` value. Any field can also be
overridden at the call site — the Python API and the CLI (`stax video --width --height --fps
--frames --first_hold --last_hold`).

---

## `floor`

```json
"floor": {
  "color": "#1a1a1a",
  "opacity": 0.04,
  "reflectivity": 0.5
}
```

**Optional.** The floor is an infinite plane at `Y = -height/2`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `color` | string | `"#1a1a1a"` | Smoked-glass tint color (hex). Dark default is barely visible on a light background. |
| `opacity` | number [0,1] | `0.04` | Floor plane opacity (~4% — "just so visible"). |
| `reflectivity` | number [0,1] | `0.5` | Strength of the blurred plate reflections on the floor. `0` = no reflection. |

The reflection is intentionally **blurry** (a Gaussian blur with radius `REFLECTION_BLUR_FRAC = 0.02` of the plate height), simulating smoked glass rather than a crisp mirror.

---

## `edge`

```json
"edge": {
  "width": 0.0,
  "color": "#f2f2f2"
}
```

**Optional.** A visible border drawn around each slide plate and each caption plate.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | number ≥ 0 | `0.0` | Border thickness as a fraction of the plate height. `0` = no border (default). Set `> 0` to enable, e.g. `0.004` for a thin border. |
| `color` | string | `"#f2f2f2"` | Border color (hex). Also the default fill and border color for caption plates (see `caption_defaults`). |

When `width = 0`, no border is drawn on either slide plates or caption plates. When `width > 0`, the same thickness applies to both.

---

## `background`

```json
"background": "#ffffff"
```

**Optional.** Default: `"#ffffff"`. Canvas background color (hex string). Used as the backdrop behind all plates and the floor.

---

## `juicy`

```json
"juicy": false
```

**Optional.** Default: `false`. **Python-only** flag. When `true`, the `juicy.py` module applies per-channel linear color correction to match the 3D render's colors to the 2D Pillow overlay. Has no effect in vexy-stax-js.

---

## `caption_defaults`

```json
"caption_defaults": {
  "size": null,
  "color": "#222222",
  "font": null,
  "fill_color": null,
  "border_color": null
}
```

**Optional.** Default styling applied to all captions that do not override it with a per-caption `style` block.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `size` | number or null | `null` | Caption text size (1 em) in scene-point units. `null` → `≈10%` of plate height. |
| `color` | string or null | `null` | Caption text color. `null` → `"#222222"`. |
| `font` | string or null | `null` | Font family or path to a `.ttf` file. `null` → bundled `vexy-stax.ttf` (Zalando Sans Expanded) in Python; `"Zalando Sans"` via Google Fonts in JS. |
| `fill_color` | string or null | `null` | Caption plate fill color. `null` → `scene.edge.color`. |
| `border_color` | string or null | `null` | Caption plate border color. `null` → `scene.edge.color`. |

---

## `caption_fade`

```json
"caption_fade": {
  "window": 0.9,
  "stagger": 0.3,
  "stagger_frames": null
}
```

**Optional.** Controls the fade-in timing of captions during a transition. Only meaningful when a `transition` is present. If omitted, the defaults listed below apply.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `window` | number (0, 1] | `0.9` | Fraction of the morph (measured from the expanded end) over which `expanded` captions fade in. `0.9` means captions start fading during the final 90% of the expand motion. |
| `stagger` | number [0, 1) | `0.3` | Back-to-front spread as a fraction of `window`. The backmost caption starts fading first; the frontmost reaches full opacity exactly at `t = 1`. |
| `stagger_frames` | integer ≥ 0 or null | `null` | Per-caption step in animation frames (overrides `stagger` when set). Useful for frame-exact stagger control. |

---

## `slides`

```json
"slides": [
  {
    "src": "layer-0-background.png",
    "gap": null,
    "opacity": 1.0,
    "caption": { "text": "Background", "show_in": "expanded" }
  }
]
```

**Required.** An array of slide objects ordered **back-to-front** (index `0` is farthest from the camera). At least one slide is required.

### Slide fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `src` | string | — | **Required.** Path to the PNG relative to the scene file, or a `data:` URI. Absolute paths are accepted too. |
| `gap` | number ≥ 0 or null | `null` | Per-slide gap override (points). `null` uses `camera.gap`. Only affects spacing between this plate and the plate behind it. |
| `opacity` | number or object | `1.0` | Plate opacity. See below. |
| `caption` | object or null | `null` | Optional text label. See below. |

### Slide opacity

Opacity can be a scalar or a per-view object:

```json
// Constant in both views
"opacity": 0.8

// Different per view, interpolated during transitions
"opacity": { "expanded": 1.0, "compact": 0.0 }
```

The per-view form is interpolated with the same easing as the camera morph. At `t=0` (compact) the opacity equals `compact`; at `t=1` (expanded) it equals `expanded`. Setting `"compact": 0` hides the slide in the compact view (equivalent to the legacy `hide` flag).

Engines clamp opacity to `[0, 1]`.

### Slide caption

```json
"caption": {
  "text": "UI Layer",
  "show_in": "expanded",
  "style": {
    "size": null,
    "color": null,
    "font": null,
    "fill_color": null,
    "border_color": null
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | — | **Required.** The caption text. |
| `show_in` | string | `"expanded"` | When the caption is visible: `"expanded"`, `"compact"`, `"both"`, or `"none"`. |
| `style` | object or null | `null` | Per-caption style overrides. Same fields as `caption_defaults`; unset fields inherit from `caption_defaults`. |

Caption plates sit to the **left** of their slide plate, sharing the same `Z` depth. Their right edge is flush with the slide plate's left edge (zero gap by default). The caption plate height is `caption_size / 0.75`, and the text occupies 75% of that height (the remaining 25% is padding above and below).
