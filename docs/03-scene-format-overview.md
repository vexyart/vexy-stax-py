---
title: Scene Format — Overview
nav_order: 4
---

# Scene Format — Overview

## One format, two implementations

The vexy-stax scene format is a single JSON document consumed identically by both packages:

- **vexy-stax-py** parses it with a strict Pydantic v2 model (`vexy_stax.scene`).
- **vexy-stax-js** parses it with a plain-object parser (`scene.js`).

The authoritative schema is published at `schema/vexy-stax-scene.schema.json` (JSON Schema draft 2020-12). Both parsers use `extra="forbid"` / `additionalProperties: false` — unknown fields fail loudly at the boundary. This is the "parse, don't validate" design: if a document is accepted, it is a valid scene.

## Minimal scene

```json
{
  "$schema": "https://vexy.art/schema/vexy-stax-scene.schema.json",
  "version": 1,
  "slides": [
    { "src": "layer-0-background.png" },
    { "src": "layer-1-content.png" },
    { "src": "layer-2-ui.png" }
  ]
}
```

All other fields have defaults. The only required fields are `version` (must be `1`) and `slides` (at least one entry with a `src`).

## Full annotated scene

```jsonc
{
  "$schema": "https://vexy.art/schema/vexy-stax-scene.schema.json",
  "version": 1,

  // Initial view to render ("expanded" or "compact")
  "view": "expanded",

  // Output canvas size in pixels (= world-space points)
  "size": { "width": 1920, "height": 1080 },

  // Camera and plate-spacing settings
  "camera": {
    "gap": 1920,          // points between adjacent plates (expanded)
    "distance": "100%",   // viewport-fit: the limiting axis fills the frame
    "angle": 60,          // azimuth degrees (expanded camera)
    "elevation": 0,       // degrees above horizon (expanded camera)
    "fov": 39.6           // horizontal FOV, ≈50 mm lens
  },

  // Animated morph between views (omit for still renders)
  "transition": {
    "kind": "expand_collapse",  // expand|collapse|expand_collapse|collapse_expand
    "duration": 3.0,            // seconds per leg
    "wait": 1.0,                // hold at the far end
    "fps": 30,
    "easing": "easeInOutCubic"
  },

  // Floor plane (smoked glass)
  "floor": {
    "color": "#1a1a1a",
    "opacity": 0.04,
    "reflectivity": 0.5
  },

  // Plate border (off by default; set width > 0 to enable)
  "edge": {
    "width": 0.0,        // fraction of plate height; 0 = no border
    "color": "#f2f2f2"   // also the default caption plate fill + border
  },

  "background": "#ffffff",

  // Python-only: per-channel color match between 3D and overlay renders
  "juicy": false,

  // Default caption styling (text + plate fill/border colors)
  "caption_defaults": {
    "size": null,          // null → 10% of plate height
    "color": "#222222",    // text color
    "font": null,          // null → bundled vexy-stax.ttf (Zalando Sans)
    "fill_color": null,    // caption plate fill; null → edge.color
    "border_color": null   // caption plate border; null → edge.color
  },

  // Caption fade-in timing during transitions
  "caption_fade": {
    "window": 0.9,          // final 90% of the morph
    "stagger": 0.3,         // back→front spread (fraction of window)
    "stagger_frames": null  // overrides stagger if set (in frames)
  },

  // Slides, ordered back-to-front (index 0 = farthest from camera)
  "slides": [
    {
      "src": "layer-0-background.png",  // path relative to scene file, or data: URI
      "gap": null,                       // null → camera.gap
      "opacity": 1.0,                    // scalar, or { "expanded": 1.0, "compact": 0.0 }
      "caption": {
        "text": "Background",
        "show_in": "expanded",           // expanded|compact|both|none
        "style": {
          "size": null,
          "color": null,
          "font": null,
          "fill_color": null,
          "border_color": null
        }
      }
    },
    {
      "src": "layer-1-content.png",
      "opacity": { "expanded": 1.0, "compact": 0.6 },
      "caption": { "text": "Content" }
    },
    {
      "src": "layer-2-ui.png",
      "caption": { "text": "UI Layer" }
    }
  ]
}
```

## Top-level structure

The scene document has these top-level properties:

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `version` | integer | yes | — | Must be `1` |
| `slides` | array | yes | — | Ordered back-to-front; ≥ 1 slide |
| `view` | string | no | `"expanded"` | Initial view |
| `size` | object | no | `{1920, 1080}` | Canvas dimensions in pixels |
| `camera` | object | no | see defaults | Camera + spacing settings |
| `transition` | object | no | `null` | Animation; omit for still renders |
| `floor` | object | no | smoked glass | Floor plane appearance |
| `edge` | object | no | `width: 0` | Plate border |
| `background` | string | no | `"#ffffff"` | Canvas background color |
| `juicy` | boolean | no | `false` | Python-only color correction |
| `caption_defaults` | object | no | `null` | Default caption styling |
| `caption_fade` | object | no | `null` | Caption fade timing |

See [Scene Format Reference](04-scene-format-reference.md) for every field's full specification.

## Generating a scene with `dir2scene`

The CLI can auto-generate a scene JSON from a directory of PNG images:

```bash
vexy-stax dir2scene assets/ --out scene.json
```

This scans the directory, sorts files naturally, auto-detects dimensions, sets a smart default gap (≈38% of scene width), and writes captions from the filenames (stripping numeric prefixes and common suffixes). All parameters are overridable via flags — see [CLI Usage](06-cli.md) for the full option list.

## Schema validation

To validate a scene file against the JSON Schema without rendering:

```python
from vexy_stax.scene import load_scene
scene = load_scene("scene.json")  # raises pydantic.ValidationError on bad input
```

Or with any JSON Schema validator:

```bash
npx ajv validate -s schema/vexy-stax-scene.schema.json -d scene.json
```
