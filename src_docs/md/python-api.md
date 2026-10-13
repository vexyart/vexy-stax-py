# Python API

Every CLI command is a thin wrapper around the package modules, so anything the CLI does you can do from Python.

| Module | Contents |
|--------|----------|
| `vexy_stax.scene` | Pydantic v2 scene model and `load_scene()` |
| `vexy_stax.geometry` | Camera poses, gaps, opacities, caption layout, frame plans |
| `vexy_stax.engines` | Engine protocol and registry |
| `vexy_stax.images` | Pillow image reading and flat compositing |
| `vexy_stax.juicy` | Per-channel colour matching between renders |
| `vexy_stax.showcase` | The showcase runner behind `example.py` |
| `vexy_stax.cli` | The `Stax` Fire CLI and `main()` |

`vexy_stax.__version__` holds the installed version.

## Render a scene

```python
from pathlib import Path

from vexy_stax.engines import available_engines, get_engine
from vexy_stax.scene import load_scene

scene = load_scene("scene.json")
print("Available:", available_engines())

pygfx = get_engine("pygfx")
pygfx.render_image(scene, "expanded", Path("beauty.png"))
pygfx.render_image(scene, "compact", Path("stack.png"))

get_engine("blender").render_video(scene, Path("morph.mp4"))
```

## `vexy_stax.scene`

### `load_scene(path)`

Reads a JSON file, validates it against the `Scene` model and resolves every slide `src` against the scene file's directory (absolute paths and `data:` URIs are kept). Invalid input raises `pydantic.ValidationError`.

```python
from vexy_stax.scene import load_scene

scene = load_scene("scene.json")
scene.slides[0].src   # absolute path string
scene.camera.gap      # float
```

### Model classes

```python
from vexy_stax.scene import (
    Scene, Slide, Caption, CaptionStyle, CaptionFade,
    Camera, Transition, Video, Floor, Edge, Size, OpacityPerView,
    View, TransitionKind, ShowIn, Easing,
)
```

Every model sets `extra="forbid"`. The type aliases are:

| Alias | Values |
|-------|--------|
| `View` | `"expanded"`, `"compact"` |
| `TransitionKind` | `"expand"`, `"collapse"`, `"expand_collapse"`, `"collapse_expand"` |
| `ShowIn` | `"expanded"`, `"compact"`, `"both"`, `"none"` |
| `Easing` | `"linear"`, `"easeInOutCubic"`, `"easeOutCubic"`, `"easeInCubic"` |

`Slide.resolved_opacity(view)` returns the slide's opacity in one view, whether `opacity` is a number or an `OpacityPerView`.

### Build a scene in code

```python
from vexy_stax.scene import Camera, Caption, Scene, Size, Slide, Transition

scene = Scene(
    size=Size(width=1920, height=1080),
    camera=Camera(gap=1200, angle=50),
    transition=Transition(kind="expand_collapse", easing="linear"),
    slides=[
        Slide(src="/abs/layer-0.png", caption=Caption(text="Background")),
        Slide(src="/abs/layer-1.png", caption=Caption(text="Content")),
        Slide(src="/abs/layer-2.png", opacity={"expanded": 1.0, "compact": 0.0}),
    ],
)
```

Paths in a scene built this way are not resolved; use absolute paths. Leave `gap` unset on a slide to inherit `camera.gap`; `gap=0` gives `MIN_GAP`.

### Save a scene

```python
from pathlib import Path

Path("scene.json").write_text(scene.model_dump_json(by_alias=True, indent=2, exclude_none=True))
```

`by_alias=True` writes the `$schema` key under its JSON name. `exclude_none=True` leaves out unset optional fields, including per-slide `gap: null`, which would otherwise read back as "minimal gap".

## `vexy_stax.geometry`

All functions take a `Scene` and return plain values. See [Geometry](geometry.md) for the formulas.

```python
from vexy_stax import geometry as g

g.compact_camera(scene)            # CameraPose
g.expanded_camera(scene)           # CameraPose
g.compact_camera(scene, viewport_aspect=2.0)

g.plate_gaps(scene)                # list[float]
g.stack_depth(scene, "expanded")   # float
g.slide_lift(scene)                # float

g.frame_plan(scene)                # list[FrameState]
g.frame_plan(scene, first_hold=0, last_hold=0)
g.transition_frames(scene)         # frames per leg
g.video_fps(scene)                 # int
g.video_dimensions(scene)          # (width, height)

g.ease("easeInOutCubic", 0.5)      # 0.5
g.interpolate_opacity(scene.slides[0], 0.5)
g.caption_opacities(scene, 0.75)   # list[float]

g.caption_size(scene)              # 1 em in points
g.caption_plate_height(scene)
g.caption_plate_center_y(scene)
g.caption_baseline_y(scene)
g.caption_anchor_x(scene)
g.caption_fill_color(scene)        # hex string
g.caption_border_color(scene)      # hex string
g.plate_edge_width(scene)          # border thickness in points

g.default_font_path()              # Path to vexy-stax.ttf, or None
```

## `vexy_stax.engines`

```python
from vexy_stax.engines import Engine, all_engines, available_engines, get_engine, is_available, register
```

| Function | Returns |
|----------|---------|
| `all_engines()` | every registered name: `['blender', 'playwright', 'pygfx']` |
| `available_engines()` | registered names whose dependency probe succeeds |
| `is_available(name)` | `True` if the probe for `name` succeeds |
| `get_engine(name)` | the engine instance; `KeyError` for an unknown name |
| `register(engine)` | registers an engine instance under `engine.name` |

`render_image(scene, view, out)` writes a PNG; `render_video(scene, out)` writes an MP4 and raises `ValueError` when the scene has no transition. See [Engines](engines.md).

## `vexy_stax.images`

```python
from vexy_stax.images import overlay_images, read_images

infos = read_images(["/abs/layer-0.png", "/abs/layer-1.png"])
# [{'path': ..., 'width': ..., 'height': ...}, ...]
overlay_images(infos, "flat.png")
```

`overlay_images` builds a canvas as large as the widest and tallest image, centres each image horizontally, aligns it to the bottom, and alpha-composites from index 0 (back) to the last (front). It is what `vexy-stax overlay` runs.

## `vexy_stax.juicy`

Per-channel linear colour correction. It compares a flat Pillow overlay with a 3D stack render and corrects the render toward the overlay's colours.

```python
from vexy_stax.juicy import apply_still, apply_video, compute_corrections

corrections = compute_corrections("flat.png", "stack.png")  # (scale, offset) per channel, B, G, R order
apply_still("beauty.png", corrections)                      # rewrites the PNG in place
apply_video("morph.mp4", corrections)                       # re-encodes the video with ffmpeg
```

`compute_corrections` matches the mean and standard deviation of each channel inside the overlay's opaque area. `apply_still` also pushes near-white pixels to pure white.

The scene's `juicy` flag records the intent, but the `render` and `video` commands don't call these functions; call them yourself.

## `vexy_stax.showcase`

`run_showcase(...)` renders a compact still, an expanded still and a short transition video of `testdata/airbl.scene.json` with each available engine into `outputs/<engine>/`, and checks that each still is not blank (pixel standard deviation above `STD_GATE = 20.0`). `example.py` in the repository root calls it. It is a development tool and expects a repository checkout.
