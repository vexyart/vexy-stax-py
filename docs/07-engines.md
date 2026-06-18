---
title: Python Rendering Engines
nav_order: 8
---

# Python Rendering Engines

vexy-stax-py ships three interchangeable render engines. All implement the same `Engine` protocol:

```python
class Engine(Protocol):
    name: str
    def render_image(self, scene: Scene, view: View, out: Path) -> None: ...
    def render_video(self, scene: Scene, out: Path) -> None: ...
```

Each engine receives its per-frame instructions from `geometry.py` — so the three engines share the same camera math and only differ in how they draw.

### Video render params and held stills (issue 335)

For **video**, all three engines read their output parameters from the scene's
[`video`](04-scene-format-reference.md#video) section, via shared `geometry.py` helpers:

- `geometry.video_dimensions(scene)` → `(width, height)` (defaults to `scene.size`),
- `geometry.video_fps(scene)` → the encoder frame rate (`video.fps`, else `transition.fps`, else 30),
- `geometry.frame_plan(scene)` → the per-frame `FrameState` list, **bookended with held stills**.

The held stills are the issue-335 §2 behavior: `frame_plan` prepends `video.first_hold` copies
of the first frame and appends `video.last_hold` copies of the last (default 10 each), so every
transition video plays `still(N) → transition → still(N)`. Because the holds are ordinary
repeated `FrameState`s, each engine keyframes them with no special handling — pygfx renders the
same deck twice, blender writes identical keyframes, playwright re-captures the same canvas.
Callers can override the holds per render: `geometry.frame_plan(scene, first_hold=…, last_hold=…)`
or `stax video --first_hold … --last_hold …`.

---

## Engine comparison

| Feature | pygfx | blender | playwright |
|---------|-------|---------|-----------|
| Speed (still) | Fast (seconds) | Slow (minutes) | Medium |
| Quality | Good | Highest | Matches JS |
| Ray-traced transparency | No | Yes (Cycles) | No |
| Soft floor reflections | Yes | Yes | Yes |
| Video output | Yes (ffmpeg) | Yes (built-in) | Yes |
| Prerequisites | wgpu GPU driver | `blender` on PATH | playwright + Chromium |
| Default for stills | **Yes** | No | No |
| Default for video | No | **Yes** | No |

---

## pygfx

**pygfx** is a GPU-accelerated renderer using WGPU (WebGPU for Python). It runs off-screen — no display or window needed — and outputs directly to PNG.

### How it works

1. Builds a WGPU off-screen canvas at `scene.size`.
2. Places plate meshes along `Z` with per-slide gaps from `geometry.plate_gaps()`.
3. Sets plate material opacity from `geometry.interpolate_opacity()`.
4. Positions a perspective camera from `geometry.expanded_camera()` or `geometry.compact_camera()`.
5. Renders the floor plane with a blurred reflection texture.
6. Renders caption plates as text meshes via `gfx.Text`, registered with the bundled vexy-stax.ttf font.
7. For video: calls `frame_plan()` for all frames, renders each, then assembles with ffmpeg (`-crf 18 -movflags +faststart`).

### pygfx camera FOV note

pygfx's `PerspectiveCamera.fov` is a *mean* of horizontal and vertical half-angles (`size = 2·near·tan(fov/2)`, `height = 2·size/(1+aspect)`), not a vertical FOV like three.js or Blender. The engine applies `_pygfx_fov_deg()` to convert the scene's horizontal FOV to pygfx's convention, ensuring compact/expanded parity ≥ 0.96 SSIM against blender and playwright.

### Availability probe

```python
import importlib.util
importlib.util.find_spec("pygfx") is not None
```

### When to use pygfx

- Quick still renders during development.
- Batch processing where Blender's startup overhead is prohibitive.
- CI smoke tests (fast, no external binary needed).

---

## blender

**blender** is a two-process renderer. The Python package builds a JSON config file, then spawns:

```
blender --background --python _blender_render.py
```

The render script (`_blender_render.py`) reads the config, constructs the Blender scene, and renders with Cycles (or Eevee in turbo mode).

### How it works

1. **Still render**: builds one camera/lighting/material setup for the requested view, renders a single frame.
2. **Video render**: builds keyframes for camera position, per-plate gap, and per-plate material opacity using the `frame_plan()` frame states, then renders the frame sequence and encodes to MP4 (`-crf 18 -movflags +faststart`).

### Blender scene construction

- Plates are `SOLIDIFY` slabs — two-faced geometry so rays pass through glass from both sides.
- Transparent materials use `transparent_max_bounces = max(64, n_plates × 4)` to handle the dense head-on stack in compact view without going black.
- The floor reflection is a blurred mirror: a Gaussian-blurred copy of the reflection texture, downscaled to ≤ 1024 px for speed (visually identical at normal floor opacity).
- Caption text objects use Blender's font object system with `align_x=RIGHT`.

### Render quality settings

| Setting | Default | Turbo (`VEXY_STAX_TURBO=1`) |
|---------|---------|------------------------------|
| Renderer | Cycles | Eevee |
| Samples | 16 | 8 |
| `max_bounces` | 4 | 4 |
| Adaptive threshold | 0.02 | 0.02 |
| OIDN denoiser | Yes | No |

### Video resolution cap

Transition videos are capped at 1920 px on the long edge (a motion preview). Still renders use the full `scene.size` resolution.

### Availability probe

```python
import shutil
shutil.which("blender") is not None
```

### When to use blender

- Final high-quality renders for publication.
- Scenes with many transparent layers (Cycles ray-traces transparency correctly; pygfx does not).
- When soft shadows and physically accurate reflections matter.

---

## playwright

**playwright** launches headless Chromium, loads a thin HTML harness page that imports the vexy-stax-js ESM build, feeds the scene, and captures output:

- **Still**: captures a canvas screenshot via Playwright's screenshot API.
- **Video**: drives the JS animation frame-by-frame via `applyFrameState()`, capturing each canvas frame, then assembles with ffmpeg.

### How it works

The engine calls `_frame_state_dict()` on each `FrameState` from `frame_plan()`, serialises it (converting snake_case `caption_opacities` to camelCase `captionOpacities` for the JS API), sends it to the page via `page.evaluate()`, and captures the canvas.

### Pixel parity

The playwright engine serves as the cross-engine parity reference: since it drives the same three.js rendering path as the browser component, it validates that the Python geometry and the JS geometry agree. Cross-engine SSIM between blender, pygfx, and playwright is ≥ 0.96 on the test scenes.

### Availability probe

```python
import importlib.util
importlib.util.find_spec("playwright") is not None
```

### When to use playwright

- Verifying that a scene renders identically in Python and in the browser.
- Testing the JS component's output as part of a Python CI pipeline.
- Debugging geometry discrepancies between Python and JS.

---

## Engine registry

Engines self-register on import. The registry is lazy — engines are only imported when first needed.

```python
from vexy_stax.engines import get_engine, available_engines, is_available

# List available engines
print(available_engines())          # e.g. ['blender', 'pygfx']

# Check a specific engine
print(is_available("blender"))      # True/False

# Get an engine by name
engine = get_engine("pygfx")
engine.render_image(scene, "expanded", Path("out.png"))
```

`get_engine()` raises `KeyError` for an unknown name. If an engine's method is not yet implemented it raises `NotImplementedError` with an actionable message — it never silently crashes.
