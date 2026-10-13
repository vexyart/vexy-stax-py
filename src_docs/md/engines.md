# Engines

vexy-stax-py has three render engines. Each implements the `Engine` protocol from `vexy_stax.engines.base`:

```python
class Engine(Protocol):
    name: str

    def render_image(self, scene: Scene, view: View, out: Path) -> None: ...

    def render_video(self, scene: Scene, out: Path) -> None: ...
```

No engine computes its own camera. Every engine takes the camera pose, gaps, plate opacities and caption opacities from `vexy_stax.geometry`, as a single pose for stills or as the `frame_plan()` list for video. The engines differ only in how they draw.

## Comparison

| | `pygfx` | `blender` | `playwright` |
|--|---------|-----------|--------------|
| Draws with | pygfx on WGPU, off-screen | Blender (Cycles, or Eevee in turbo mode) in a subprocess | vexy-stax-js three.js stage in headless Chromium |
| Default for | `render` | `video` | — |
| Stills | supersampled ×2, Lanczos downscale | full `scene.size` | supersampled ×2, Lanczos downscale |
| Video | PNG sequence + ffmpeg | PNG sequence + ffmpeg, long edge capped at 1920 px | captured frames + ffmpeg |
| Needs | WGPU backend; ffmpeg for video | Blender binary; ffmpeg for video | Chromium for Playwright, a built sibling `vexy-stax-js`, ffmpeg for video |

All three encode video as H.264 with `-crf 18` and `+faststart`.

## Video parameters

For video, every engine reads the same helpers from `vexy_stax.geometry`:

- `video_dimensions(scene)`: `(video.width or size.width, video.height or size.height)`,
- `video_fps(scene)`: `video.fps`, else `transition.fps`, else 30,
- `frame_plan(scene)`: the list of `FrameState` objects, including the held first and last frames.

The held frames are plain repeated `FrameState` objects, so engines need no special handling for them. A scene without a `transition` cannot be rendered as video; the engine raises `ValueError: scene has no transition; nothing to animate (use render_image)`.

## pygfx

The default for stills. It renders off-screen through `rendercanvas.offscreen`, so it needs no window or display.

What it builds:

- one textured plane per slide, sized to the image's pixel dimensions,
- a floor plane at the bottom of the deck, drawn with `floor.color` and `floor.opacity`,
- a faded, blurred mirror copy of each plate below the floor line for the reflection (`floor.reflectivity`),
- caption plates: an opaque quad with an optional border and centred text, registered with the bundled `vexy-stax.ttf` unless the scene sets another font,
- a perspective camera from `compact_camera()` or `expanded_camera()`.

Plates cast no shadow on the floor.

pygfx's `PerspectiveCamera.fov` is not a horizontal field of view, so the engine converts the scene's horizontal `fov` before use. That keeps its framing equal to Blender and three.js.

For video it renders each `FrameState` to a PNG and assembles the sequence with ffmpeg. Missing ffmpeg raises `FileNotFoundError: ffmpeg not found on PATH`.

Use pygfx for quick stills, batch work and tests: it starts in seconds and needs no external program for stills.

## blender

The default for video. The Python side builds a job description (plates, camera, captions, frames) and runs Blender in the background with the bundled script, passing the job as JSON after `--`:

```text
blender --background --python vexy_stax/engines/_blender_render.py -- '{...job JSON...}'
```

The script builds the scene inside Blender and renders it.

Finding Blender: `blender` on `PATH`, then `/opt/homebrew/bin/blender`, then `/Applications/Blender.app/Contents/MacOS/Blender`. If none exists it raises `FileNotFoundError` with an install hint.

Render settings:

| Setting | Default | With `VEXY_STAX_TURBO=1` |
|---------|---------|--------------------------|
| Renderer | Cycles | Eevee |
| Samples | 16 | 8 |
| Denoiser | OpenImageDenoise | — |
| Cycles `max_bounces` | 4 | — |
| Cycles `transparent_max_bounces` | `max(64, 4 × number of plates)` | — |

The high transparent-bounce limit keeps the dense head-on stack of the compact view from rendering black.

For video, the engine keys every frame from `frame_plan()`, renders a PNG sequence and assembles it with ffmpeg. It caps the video's long edge at 1920 pixels, keeping the aspect ratio: a 3840 × 2480 scene renders a 1920 × 1240 video. Stills use the full `scene.size`.

Use Blender for final output, especially decks with many transparent layers.

## playwright

The Playwright engine reuses the browser renderer instead of drawing on its own:

1. It serves the directory that contains both checkouts over a local HTTP server, so textures load without `file://` restrictions.
2. It opens a generated harness page in headless Chromium. The page loads `vexy-stax-js/dist/vexy-stax.element.js` and mounts the scene in a `<vexy-stax>` element. Slide paths are rewritten to `http://` URLs under the served root.
3. For a still, it screenshots the WebGL canvas.
4. For video, it computes `frame_plan()` in Python, sends each `FrameState` to the page's `stage.applyFrameState`, captures the canvas, and assembles the frames with ffmpeg.

The engine locates the bundle at `../vexy-stax-js/dist/vexy-stax.element.js` relative to the `vexy-stax-py` checkout. If it is missing, rendering fails with `FileNotFoundError` and the build command. It therefore works from a development checkout of both repositories, not from a wheel installed on its own.

Use it to compare the Python output with what the browser component renders.

## Registry

Engines register themselves when `vexy_stax.engines` first needs them.

```python
from pathlib import Path

from vexy_stax.engines import all_engines, available_engines, get_engine, is_available
from vexy_stax.scene import load_scene

print(all_engines())          # ['blender', 'playwright', 'pygfx']
print(available_engines())    # only those whose probe succeeds
print(is_available("blender"))

engine = get_engine("pygfx")  # KeyError for an unknown name
engine.render_image(load_scene("scene.json"), "expanded", Path("beauty.png"))
```

The availability probes are cheap: `shutil.which("blender")` for Blender, and `importlib.util.find_spec(...)` for `pygfx` and `playwright`.

## Adding an engine

1. Create `src/vexy_stax/engines/myengine.py` with a class that has `name = "myengine"`, `render_image()` and `render_video()`. Raise `NotImplementedError` for anything not supported yet; the CLI reports it as "not ready".
2. Take every camera pose and per-frame value from `vexy_stax.geometry`; don't recompute them.
3. Call `register(MyEngine())` at module level.
4. Add an availability probe for `"myengine"` to `_PROBES` in `engines/base.py`.
5. Import the module in `_ensure_loaded()` in `engines/base.py`.
6. Add tests with a pytest marker that skips when the engine is unavailable, like the existing `blender`, `pygfx` and `playwright` markers in `pyproject.toml`.
