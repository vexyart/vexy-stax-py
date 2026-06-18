---
title: Programmatic Python API
nav_order: 12
---

# Programmatic Python API

vexy-stax-py is a fully usable library, not just a CLI tool. All CLI commands are thin wrappers around the public Python API.

---

## Package layout

```
vexy_stax/
├── scene.py        Pydantic v2 scene model + load_scene()
├── geometry.py     Pure view math: cameras, gaps, opacities, captions
├── engines/
│   ├── base.py     Engine protocol + registry (get_engine, available_engines)
│   ├── blender.py  Blender two-process renderer
│   ├── pygfx.py    WGPU off-screen renderer
│   └── playwright.py  Headless Chromium renderer
├── images.py       Pillow flat composite (overlay_images)
└── juicy.py        Per-channel color correction
```

---

## `vexy_stax.scene`

### `load_scene(path)`

Read, validate, and path-resolve a scene JSON file. Returns a `Scene` object.

```python
from vexy_stax.scene import load_scene

scene = load_scene("scene.json")
# scene.slides[0].src is now an absolute path
# scene.camera.gap == 1920.0 (or whatever was in the file)
```

Each slide `src` is resolved relative to the scene file's directory into an absolute path. `data:` URIs are left untouched. Validation errors are Pydantic's own `ValidationError`, which names the offending field.

### Scene model classes

All models use `extra="forbid"` — unknown fields raise `ValidationError` at parse time.

```python
from vexy_stax.scene import (
    Scene, Slide, Caption, CaptionStyle, CaptionFade,
    Camera, Transition, Floor, Edge, Size,
    OpacityPerView, View, TransitionKind, ShowIn, Easing,
)
```

**`Scene`** — top-level document:

```python
scene.version          # Literal[1]
scene.view             # "expanded" | "compact"
scene.size             # Size(width=1920, height=1080)
scene.camera           # Camera(gap=1920, distance="100%", angle=60, elevation=0, fov=39.6)
scene.transition       # Transition | None
scene.floor            # Floor(color="#1a1a1a", opacity=0.04, reflectivity=0.5)
scene.edge             # Edge(width=0.0, color="#f2f2f2")
scene.background       # "#ffffff"
scene.juicy            # False
scene.caption_defaults # CaptionStyle | None
scene.caption_fade     # CaptionFade | None
scene.slides           # list[Slide]
```

**`Slide`**:

```python
slide.src                         # absolute path string (after load_scene)
slide.gap                         # float | None
slide.opacity                     # float | OpacityPerView
slide.caption                     # Caption | None
slide.resolved_opacity("expanded") # float — resolves scalar or per-view
```

**`Caption`**:

```python
caption.text      # str
caption.show_in   # "expanded" | "compact" | "both" | "none"
caption.style     # CaptionStyle | None
```

**`Transition`**:

```python
tr.kind      # "expand" | "collapse" | "expand_collapse" | "collapse_expand"
tr.duration  # float (seconds per leg)
tr.wait      # float (hold at far end)
tr.fps       # int
tr.easing    # "linear" | "easeInOutCubic" | "easeOutCubic" | "easeInCubic"
```

### Constructing a scene programmatically

```python
from vexy_stax.scene import (
    Scene, Slide, Caption, Camera, Transition, Floor, Edge, Size
)

scene = Scene(
    version=1,
    size=Size(width=1920, height=1080),
    camera=Camera(gap=1920, distance="100%", angle=60, fov=39.6),
    transition=Transition(
        kind="expand_collapse",
        duration=3.0,
        wait=1.0,
        fps=30,
        easing="easeInOutCubic",
    ),
    slides=[
        Slide(src="/abs/path/to/layer-0.png", caption=Caption(text="Background")),
        Slide(src="/abs/path/to/layer-1.png", caption=Caption(text="Content")),
        Slide(
            src="/abs/path/to/layer-2.png",
            opacity={"expanded": 1.0, "compact": 0.0},
            caption=Caption(text="UI"),
        ),
    ],
)
```

### Serialising a scene

```python
# Compact JSON string
json_str = scene.model_dump_json(by_alias=True, indent=2)

# Python dict
data = scene.model_dump(by_alias=True)
```

---

## `vexy_stax.geometry`

Pure, engine-agnostic geometry. All functions take a `Scene` object and return plain Python values.

### Camera poses

```python
from vexy_stax.geometry import compact_camera, expanded_camera, CameraPose

compact  = compact_camera(scene)    # CameraPose
expanded = expanded_camera(scene)   # CameraPose

# CameraPose fields:
compact.position   # tuple[float, float, float]  — world XYZ
compact.target     # tuple[float, float, float]  — look-at point
compact.fov        # float  — horizontal FOV in degrees
compact.near       # float  — near clipping plane
```

Both accept an optional `viewport_aspect: float` argument (width/height). The default is the scene aspect ratio, which is what the offline renderers use. The live browser element passes its actual container aspect so the deck fills the viewport correctly.

### Plate layout

```python
from vexy_stax.geometry import plate_gaps, stack_depth

gaps  = plate_gaps(scene)              # list[float] — per-slide gap
depth = stack_depth(scene, "expanded") # float — total Z extent
depth = stack_depth(scene, "compact")  # float — (N-1) × MIN_GAP
```

### Transition frame plan

```python
from vexy_stax.geometry import frame_plan, FrameState

states = frame_plan(scene)   # list[FrameState]; empty if no transition

# FrameState fields:
state = states[0]
state.camera           # CameraPose
state.gaps             # list[float] — per-slide gap at this frame
state.opacities        # list[float] — per-slide plate opacity
state.caption_opacities  # list[float] — per-slide caption opacity
```

Frame count:

```python
# For expand_collapse, duration=3.0, wait=1.0, fps=30:
len(states)  # 2 × (90 + 30) = 240
```

### Caption geometry

```python
from vexy_stax.geometry import (
    caption_size,
    caption_anchor_x,
    caption_plate_center_y,
    caption_baseline_y,
    caption_plate_height,
    caption_fill_color,
    caption_border_color,
    plate_edge_width,
)

em     = caption_size(scene)              # 1em in world points
ax     = caption_anchor_x(scene)          # right edge X for all captions
cy     = caption_plate_center_y(scene)    # caption plate center Y
by     = caption_baseline_y(scene)        # text baseline Y
ph     = caption_plate_height(scene)      # caption plate height
fill   = caption_fill_color(scene)        # hex string
border = caption_border_color(scene)      # hex string
ew     = plate_edge_width(scene)          # border thickness in points
```

### Opacity and easing

```python
from vexy_stax.geometry import (
    interpolate_opacity,
    caption_opacities,
    ease,
)

# Plate opacity at morph factor t (0=compact, 1=expanded)
op = interpolate_opacity(slide, t=0.5)

# All caption opacities at t
caps = caption_opacities(scene, t=0.75)  # list[float]

# Easing curves
v = ease("easeInOutCubic", 0.5)   # 0.5
v = ease("linear", 0.3)           # 0.3
v = ease("easeOutCubic", 0.8)     # ~0.992
```

### Default font path

```python
from vexy_stax.geometry import default_font_path
path = default_font_path()   # Path to vexy-stax.ttf, or None
```

---

## `vexy_stax.engines`

### Registry functions

```python
from vexy_stax.engines import get_engine, available_engines, is_available, all_engines

# List engines available in this environment
print(available_engines())     # ['blender', 'pygfx']

# Check a specific engine
print(is_available("blender")) # True/False

# All registered engine names (regardless of availability)
print(all_engines())           # ['blender', 'pygfx', 'playwright']

# Get a specific engine (raises KeyError if unknown)
engine = get_engine("pygfx")
```

### Rendering

```python
from pathlib import Path

# Render a still
engine.render_image(scene, view="expanded", out=Path("beauty.png"))
engine.render_image(scene, view="compact",  out=Path("stack.png"))

# Render a transition video (uses scene.transition settings)
engine.render_video(scene, out=Path("morph.mp4"))
```

Both methods raise `NotImplementedError` with an actionable message if the engine cannot perform the operation (e.g., video is not yet implemented for that engine). They never silently crash.

### Complete render example

```python
from pathlib import Path
from vexy_stax.scene import load_scene
from vexy_stax.engines import get_engine, available_engines

scene = load_scene("scene.json")

print("Available engines:", available_engines())

# Render expanded view with pygfx
engine = get_engine("pygfx")
engine.render_image(scene, "expanded", Path("outputs/beauty.png"))
engine.render_image(scene, "compact",  Path("outputs/stack.png"))

# Render transition video with blender
engine = get_engine("blender")
engine.render_video(scene, Path("outputs/morph.mp4"))
```

---

## `vexy_stax.images`

Pillow-based 2D flat compositing — no 3D engine required.

```python
from vexy_stax.images import read_images, overlay_images

# Read image metadata (width, height, path)
infos = read_images(["/path/to/layer-0.png", "/path/to/layer-1.png"])

# Composite all layers into a flat PNG
overlay_images(infos, "flat.png")
```

`overlay_images` stacks the images in order (index 0 at the bottom, last on top), compositing with PIL's RGBA alpha blending.

---

## `vexy_stax.juicy`

Per-channel linear color correction. Enabled by setting `juicy: true` in the scene JSON (Python-only flag). The `juicy.py` module matches the color distribution of the 3D render to the 2D Pillow overlay via per-channel linear correction, compensating for renderer color space differences.

This is called automatically by the engines when `scene.juicy == True`. You can also call it directly:

```python
from vexy_stax.juicy import match_colors
corrected = match_colors(source_image, reference_image)
```
