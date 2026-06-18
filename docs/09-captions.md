---
title: Captions & Layout
nav_order: 10
---

# Captions & Layout

## Overview

Each slide can carry an optional **caption** — a text label rendered as a small bordered plate sitting to the **left** of the slide plate at the same `Z` depth. Captions fade in as the deck expands, staggered back-to-front, and disappear in the compact view (by default).

All caption geometry is computed once in `geometry.py` / `geometry.js` and consumed identically by all four renderers, so caption positions, sizes, and opacities are frame-exact across engines.

---

## Caption plates

A caption is not floating text — it is a **small opaque bordered plate** with the text centered on it.

### Dimensions

Let `em = caption_size(scene)` (the nominal text size in world-space points):

| Property | Formula | Default (1920×1080 scene) |
|----------|---------|--------------------------|
| Text size (1em) | `caption_defaults.size` or `height × 0.10` | ≈108 pt |
| Plate height | `em / 0.75` | ≈144 pt |
| Plate width | text width + `0.75em` padding each side | varies |
| Border width | `scene.edge.width × scene.size.height` | 0 (off by default) |

The plate height formula keeps the text at 75% of the plate height regardless of whether the size is the default or explicitly set.

### Position

All caption plates share the same world `X` anchor point, computed once:

```python
caption_anchor_x(scene) = -(scene.size.width / 2.0 + CAPTION_GAP_EM × caption_size(scene))
```

`CAPTION_GAP_EM = 0.0` (the gap is zero — the caption plate's right edge is flush against the slide plate's left edge). Each caption plate's **right edge** lands at `caption_anchor_x`.

The vertical position:

```python
caption_plate_center_y(scene) = -(scene.size.height / 2.0) + caption_plate_height(scene) / 2.0
```

The caption plate sits on the virtual ground (floor level = `Y = -height/2`), with its center half a plate-height above.

Each caption plate keeps its **slide's Z position**, so in the angled expanded view the caption plates recede in depth alongside their slide plates.

### Colors

| Element | Default | Override |
|---------|---------|---------|
| Caption text | `#222222` | `caption_defaults.color` or `caption.style.color` |
| Caption plate fill | `scene.edge.color` (`#f2f2f2`) | `caption_defaults.fill_color` |
| Caption plate border | `scene.edge.color` (`#f2f2f2`) | `caption_defaults.border_color` |

When `scene.edge.width = 0` (the default), no border is drawn on caption plates either.

### Font

The default caption font is the bundled **vexy-stax.ttf** (Zalando Sans Expanded, wdth 125 / wght 500), shipped inside the Python wheel. The JS engine matches it with the Google Font "Zalando Sans" at the same variation axis values.

```python
from vexy_stax.geometry import default_font_path
font = default_font_path()   # Path to vexy-stax.ttf, or None
```

Override per scene or per caption:

```json
"caption_defaults": { "font": "/path/to/MyFont.ttf" }
```

Font support is engine-best-effort: Blender needs a loadable font file path; pygfx uses the font manager; JS uses CSS font-family.

---

## `show_in` — visibility per view

| `show_in` value | Compact | Expanded | During transition |
|----------------|---------|----------|------------------|
| `"expanded"` (default) | 0 | 1 | Fades in as `t → 1` |
| `"compact"` | 1 | 0 | Fades out as `t → 1` |
| `"both"` | 1 | 1 | Always 1 |
| `"none"` | 0 | 0 | Always 0 |

---

## Caption fade timing

When a transition is running, `expanded` captions fade in using a staggered window defined by `caption_fade`:

```json
"caption_fade": {
  "window": 0.9,
  "stagger": 0.3,
  "stagger_frames": null
}
```

### Window

`window` (default `0.9`) is the fraction of the expand leg over which captions become visible. With `window = 0.9`, captions only start fading in during the **final 90%** of the morph (i.e., from `t = 0.1` to `t = 1.0`).

### Stagger

`stagger` (default `0.3`) spreads the per-caption fade onset back-to-front as a fraction of the window. With default values:

- Spread = `stagger × window = 0.3 × 0.9 = 0.27` of the full morph range.
- The **backmost** caption (index 0) starts fading at `t = 1 − window = 0.10`.
- The **frontmost** caption reaches full opacity exactly at `t = 1.0`.
- Captions in between start linearly between those two.

This creates the effect of labels "materializing" from back to front as the deck fans open.

### Stagger frames

`stagger_frames` (integer, optional) sets the per-caption step in transition **frames** instead of as a fraction of the window. Useful for frame-exact control:

```json
"caption_fade": { "stagger_frames": 3 }
```

With 30 fps and `duration = 3.0` (90 frames per leg), `stagger_frames = 3` gives a 3-frame (0.1 s) step between each caption.

### `compact` captions

Captions with `show_in: "compact"` fade **out** linearly as the deck expands (`opacity = 1 - t`). They are fully visible in the compact view and gone in the expanded view.

---

## `caption_opacities` function

The geometry module exposes `caption_opacities(scene, t)` which returns the per-slide caption opacity list at morph factor `t`. All engines call this once per frame:

```python
from vexy_stax.geometry import caption_opacities

# At t=0 (compact view): all expanded captions are 0
opacs = caption_opacities(scene, 0.0)   # [0.0, 0.0, 0.0, ...]

# At t=1 (expanded view): all expanded captions are 1
opacs = caption_opacities(scene, 1.0)   # [1.0, 1.0, 1.0, ...]

# Mid-transition: staggered fade
opacs = caption_opacities(scene, 0.75)  # [0.83, 0.56, 0.28, ...]
```

This function is pure — no rendering dependencies — and produces identical results in `geometry.py` and `geometry.js`.

---

## Scene JSON example

```json
{
  "caption_defaults": {
    "size": 108,
    "color": "#222222",
    "font": null
  },
  "caption_fade": {
    "window": 0.9,
    "stagger": 0.3
  },
  "slides": [
    {
      "src": "layer-0-bg.png",
      "caption": { "text": "Background", "show_in": "expanded" }
    },
    {
      "src": "layer-1-content.png",
      "caption": {
        "text": "Content",
        "show_in": "expanded",
        "style": { "color": "#0066cc" }
      }
    },
    {
      "src": "layer-2-ui.png",
      "caption": { "text": "UI", "show_in": "both" }
    }
  ]
}
```

---

## Disabling captions

Set `show_in: "none"` on individual captions, or omit the `caption` key entirely:

```json
{ "src": "layer.png" }
```

To turn off captions at the `dir2scene` stage:

```bash
vexy-stax dir2scene assets/ --captions false --out scene.json
```
