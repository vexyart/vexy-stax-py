---
title: Core Concepts & Coordinate System
nav_order: 3
---

# Core Concepts & Coordinate System

## The scene

A **scene** is an ordered list of **slides** (back-to-front; index 0 is farthest from the camera) plus camera, floor, transition, and caption settings. Everything is expressed in a single JSON document that both vexy-stax-py and vexy-stax-js consume identically.

## Slides and plates

Each **slide** is a flat upright rectangular plate rendered in 3D. Slides are:

- **Bottom-aligned** to the tallest slide in the deck.
- **Horizontally centered** at `X = 0`.
- **Vertically centered** so the middle of the tallest slide sits at `Y = 0`.
- **Standing on the floor** at `Z = 0` (the floor runs just below `Y = -height/2`).

The source image for each slide is a PNG file (or a `data:` URI). Plate dimensions in world-space points equal the pixel dimensions of the source image.

## The deck

The **deck** is the full collection of plates stacked along the Z axis. Plates are ordered back-to-front:

- The **frontmost** plate (last in the `slides` array) sits at `Z = 0`.
- Each plate behind it is offset further along `-Z` by its **gap** value.
- The **backmost** plate (index 0) sits at `Z = -stack_depth`.

## Two views

vexy-stax defines exactly two views:

### Expanded view

```
alias: "beauty", "angled", "hero-shot start"
```

- The camera orbits to an oblique angle (azimuth + elevation).
- Plates are spaced apart by `camera.gap` (plus per-slide overrides).
- Captions are visible (they fade in with the staggered animation).
- Designed to show the layering structure of the artwork.

### Compact view

```
alias: "stack", "hero", "straight-on"
```

- The camera sits head-on on the `+Z` axis aimed at the deck center.
- Plates collapse to `MIN_GAP = 3 pt` — just enough separation to avoid Z-fighting.
- Captions with `show_in: "expanded"` are hidden.
- Designed to show the artwork as a coherent composite.

## Transitions

A **transition** animates between the two views over `duration` seconds. Four kinds are available:

| `kind` | Animation |
|--------|-----------|
| `expand` | compact → expanded |
| `collapse` | expanded → compact |
| `expand_collapse` | compact → expanded → compact (round-trip) |
| `collapse_expand` | expanded → compact → expanded (round-trip) |

During a transition the engine interpolates:

1. **Camera position and target** — spherical orbit between the two camera poses.
2. **Per-slide gap** — lerp between `MIN_GAP` (compact) and `camera.gap` (expanded).
3. **Per-slide opacity** — lerp between the compact and expanded opacity values using the same easing curve.
4. **Per-slide caption opacity** — staggered fade governed by `caption_fade`.

An optional `wait` hold (default 1 s) freezes the camera at the far end of a leg before the return trip.

## The floor

The **floor** is an infinite plane at `Y = -height/2` — just below the bottom of the plates. It renders as smoked glass:

- A dark tint (`color`, default `#1a1a1a`), `opacity` ~4% — barely visible on a light background.
- A **blurred** (not crisp) reflection of the plates (`reflectivity`, default 0.5). The reflection blur is computed as `REFLECTION_BLUR_FRAC = 0.02` of the plate height, giving a soft mirror effect without distracting sharpness.

## Captions

**Captions** are text labels attached to individual slides. Each caption renders as a small opaque bordered plate placed to the **left** of its slide plate. The caption plate:

- Has the same border color and style as the slide plates (`scene.edge`).
- Has height `≈13.3%` of the frontmost plate height (the default; adjustable via `caption_defaults.size`).
- Carries its text centered on it with 0.75 em padding on each side.
- Shares its slide's `Z` position so it recedes in depth alongside its plate in the expanded view.

Captions with `show_in: "expanded"` (the default) are invisible in the compact view and fade in as the deck expands, staggered back-to-front.

## Coordinate system

vexy-stax uses a **Y-up right-handed coordinate frame** matching three.js:

| Axis | Meaning |
|------|---------|
| `X` | Plate width, centered at 0 |
| `Y` | Vertical (up). Plate centers at `Y = 0`; floor at `Y = -height/2` |
| `Z` | Depth. Front plate at `Z = 0`; `+Z` toward viewer; back plate at `Z = -stack_depth` |

Both the Blender render script and the three.js JS stage build the scene in this one frame, so camera poses are exchangeable between renderers.

## Easing

All interpolation during a transition uses one of four named easing curves:

| Name | Formula |
|------|---------|
| `linear` | `t` |
| `easeInOutCubic` | default; smooth acceleration and deceleration |
| `easeOutCubic` | fast start, slow finish |
| `easeInCubic` | slow start, fast finish |

Both `geometry.py` and `geometry.js` evaluate these identically, ensuring frame-exact parity across renderers.

## Opacity

Each slide has an **opacity** that can be:

- A **scalar** (`0.9`) — constant in both views.
- A **per-view object** (`{ "expanded": 1.0, "compact": 0.4 }`) — interpolated during transitions using the same easing curve as camera/spacing.

Opacity multiplies the slide's image alpha (premultiplied). `0` makes the slide fully invisible. Setting `compact: 0` reproduces the legacy `hide` behavior (the slide is visible only in expanded).
