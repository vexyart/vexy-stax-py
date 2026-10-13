# Scene format

## One format, two readers

A scene is one JSON document. Both packages read it:

- vexy-stax-py parses it into the Pydantic v2 model in `vexy_stax.scene`.
- vexy-stax-js parses it with its own `scene.js`.

The JSON Schema is `schema/vexy-stax-scene.schema.json` (draft 2020-12, `$id` `https://vexy.art/schema/vexy-stax-scene.schema.json`). Both readers reject unknown fields: every Pydantic model sets `extra="forbid"`, and the schema sets `additionalProperties: false`. A typo in a field name fails loudly when the scene is loaded instead of being silently ignored.

## Minimal scene

```json
{
  "version": 1,
  "slides": [
    { "src": "layer-0-background.png" },
    { "src": "layer-1-content.png" },
    { "src": "layer-2-ui.png" }
  ]
}
```

The schema requires `version` (always `1`) and `slides` (at least one entry with a `src`). Every other field has a default.

## Annotated scene

The comments below are for explanation only; JSON itself does not allow comments.

```jsonc
{
  "$schema": "https://vexy.art/schema/vexy-stax-scene.schema.json", // optional, ignored
  "version": 1,
  "view": "expanded",                       // initial view: expanded | compact
  "size": { "width": 1920, "height": 1080 },// output size in pixels (= points)

  "camera": {
    "gap": 1920,          // points between adjacent plates in the expanded view
    "distance": "100%",   // absolute points, or "P%" fit of the frontmost plate
    "angle": 60,          // expanded camera azimuth, degrees
    "elevation": 0,       // expanded camera elevation, degrees
    "fov": 39.6           // horizontal field of view, degrees
  },

  "transition": {         // omit for still-only scenes
    "kind": "expand_collapse",
    "duration": 3.0,      // seconds per leg
    "wait": 1.0,          // hold after each leg, seconds
    "fps": 30,
    "easing": "easeInOutCubic"
  },

  "video": {              // video output settings; all optional
    "width": null, "height": null, "fps": null, "frames": null,
    "first_hold": 10, "last_hold": 10
  },

  "floor": { "color": "#ffffff", "opacity": 0.0, "reflectivity": 0.1 },
  "edge":  { "width": 0.0, "color": "#f2f2f2" },
  "background": "#ffffff",
  "juicy": false,
  "captions": true,       // global caption switch

  "caption_defaults": {   // default caption style
    "size": null, "color": null, "font": null,
    "fill_color": null, "border_color": null
  },
  "caption_fade": { "window": 0.9, "stagger": 0.3, "stagger_frames": null },

  "slides": [             // back to front; index 0 is the farthest plate
    {
      "src": "layer-0-background.png",
      "caption": { "text": "Background" }
    },
    {
      "src": "layer-1-content.png",
      "opacity": { "expanded": 1.0, "compact": 0.6 },
      "caption": { "text": "Content", "show_in": "expanded" }
    },
    {
      "src": "layer-2-ui.png",
      "gap": 400,
      "caption": { "text": "UI", "style": { "color": "#0066cc" } }
    }
  ]
}
```

## Top-level fields

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `version` | integer | `1` | Format version. Must be `1`. |
| `slides` | array | — | Slides, back to front. At least one. |
| `view` | string | `"expanded"` | Initial view. |
| `size` | object | `1920 × 1080` | Output size in pixels. |
| `camera` | object | see reference | Camera and expanded spacing. |
| `transition` | object or null | `null` | The animation. Required for video. |
| `video` | object | see reference | Video size, frame rate and held frames. |
| `floor` | object | invisible pane, faint reflection | Floor appearance. |
| `edge` | object | `width` 0 | Plate borders. |
| `background` | string | `"#ffffff"` | Background colour. |
| `juicy` | boolean | `false` | Python-only colour-matching flag. |
| `captions` | boolean | `true` | Draw caption plates at all. |
| `caption_defaults` | object or null | `null` | Default caption style. |
| `caption_fade` | object or null | `null` | Caption fade timing. |
| `$schema` | string | — | Optional schema pointer; accepted and ignored. |

Every field is described in the [Scene reference](scene-reference.md).

## How slide paths are resolved

`load_scene()` resolves each slide's `src` against the directory of the scene file and stores the absolute path. Absolute paths stay as they are. `data:` URIs are left untouched.

For a scene at `/work/deck/scene.json`:

| `src` in the file | After loading |
|-------------------|---------------|
| `layers/a.png` | `/work/deck/layers/a.png` |
| `../shared/b.png` | `/work/shared/b.png` |
| `/abs/c.png` | `/abs/c.png` |
| `data:image/png;base64,...` | unchanged |

## Generating a scene

`vexy-stax dir2scene DIRECTORY` writes a complete scene from a folder of images. See [Quick start](quickstart.md) for a worked example and [CLI](cli.md#dir2scene) for every flag. Note the per-slide `"gap": null` issue described there.

## Validating a scene

Load it with the Python model. Invalid input raises `pydantic.ValidationError`, which names the offending field:

```python
from vexy_stax.scene import load_scene

scene = load_scene("scene.json")
```

Any JSON Schema validator also works against `schema/vexy-stax-scene.schema.json`.
