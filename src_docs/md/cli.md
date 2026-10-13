# CLI

The `vexy-stax` command is built with [Fire](https://github.com/google/python-fire) and Rich. Every subcommand is a method of the `Stax` class in `src/vexy_stax/cli.py`. `python -m vexy_stax` runs the same CLI.

```text
vexy-stax COMMAND [ARGS] [FLAGS]

  dir2scene   Generate a scene JSON from a directory of images
  render      Render one still in the expanded or compact view
  video       Render the scene's transition to a video file
  overlay     Flat Pillow composite of the slides, no 3D engine
  engines     List the engines whose dependencies are available
```

`vexy-stax COMMAND --help` prints the flags of one command.

## Flag syntax

Fire accepts several spellings. All of these work:

```bash
vexy-stax render scene.json --view compact
vexy-stax render scene.json --view=compact
vexy-stax dir2scene assets --floor_color '#000000'
vexy-stax dir2scene assets --floor-color '#000000'
```

Boolean flags need care:

| To set | Write | Not |
|--------|-------|-----|
| `True` | `--reverse` or `--reverse=True` | |
| `False` | `--nocaptions` or `--captions=False` | `--captions false` or `--captions=false` (Fire reads lowercase `false` as a non-empty string, which counts as true) |

## `dir2scene`

Generate a scene JSON from a folder of images.

```bash
vexy-stax dir2scene DIRECTORY [FLAGS]
```

`DIRECTORY` must contain at least one `.png`, `.jpg`, `.jpeg` or `.webp` file (the extension check ignores case). Files are sorted in natural order and become slides back to front. The command prints the absolute path of the scene it wrote.

| Flag | Default | Meaning |
|------|---------|---------|
| `--out` | `scene.json` | Output path. If it is an existing directory, `scene.json` is written inside it. |
| `--view` | `expanded` | Value for the scene's `view` field. |
| `--width` | first image's width | `size.width`. |
| `--height` | first image's height | `size.height`. |
| `--gap` | `int(width × 0.38)` | `camera.gap` in points. |
| `--distance` | `100%` | `camera.distance`. |
| `--angle` | `60.0` | `camera.angle`. |
| `--elevation` | `0.0` | `camera.elevation`. |
| `--fov` | `39.6` | `camera.fov`. |
| `--background` | `#ffffff` | `background`. |
| `--floor_color` | `#f2f2f2` | `floor.color`. |
| `--floor_opacity` | `1.0` | `floor.opacity`. |
| `--floor_reflectivity` | `0.5` | `floor.reflectivity`. |
| `--transition_kind` | none | Adds a `transition` block of this kind. Without it, the scene has no transition. |
| `--transition_duration` | `3.0` | `transition.duration`. |
| `--transition_wait` | `1.0` | `transition.wait`. |
| `--transition_fps` | `30` | `transition.fps`. |
| `--transition_easing` | `easeInOutCubic` | `transition.easing`. |
| `--reverse` | `False` | Reverse the file order (use it when the folder is sorted front to back). |
| `--captions` | `True` | Generate a caption per slide from its file name. `--nocaptions` turns this off. |
| `--juicy` | `False` | Value for the scene's `juicy` field. |

Slide paths are written relative to the output file. Each generated caption uses `show_in: "expanded"`.

**How captions are named.** The prefix shared by all file names is removed, then leading and trailing digits, spaces, `-` and `_`, then `-` and `_` become spaces and the result is title-cased. An empty result becomes `Slide`. In `testdata/airbl-lores/` the shared prefix is `airbl-0`, so `airbl-020-source.png` becomes `Source`.

!!! warning
    The generated scene contains `"gap": null` for every slide. An explicit `null` gap means minimal spacing, so the expanded view collapses. Remove the keys, for example with `jq 'del(.slides[].gap)'`. See [Troubleshooting](troubleshooting.md#expanded-view-looks-collapsed).

Examples:

```bash
# Scene with a round-trip transition
vexy-stax dir2scene assets --out scene.json \
  --transition_kind expand_collapse --transition_easing linear

# 4K canvas, 45° camera, no captions
vexy-stax dir2scene assets --out scene.json \
  --width 3840 --height 2160 --angle 45 --nocaptions
```

## `render`

Render one still.

```bash
vexy-stax render SCENE [--view expanded|compact] [--engine NAME] [--out PATH]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--view` | `expanded` | View to render. The scene's own `view` field is not used. |
| `--engine` | `pygfx` | `pygfx`, `blender` or `playwright`. |
| `--out` | `out.png` | Output PNG. |

On success it prints `Wrote OUT (engine: NAME)`.

```bash
vexy-stax render scene.json --view expanded --out beauty.png
vexy-stax render scene.json --view compact --engine blender --out stack.png
```

## `video`

Render the scene's transition to a video file. The scene must contain a `transition` block.

```bash
vexy-stax video SCENE [FLAGS]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--engine` | `blender` | `blender`, `pygfx` or `playwright`. |
| `--out` | `out.mp4` | Output video. |
| `--width` | scene `video.width` | Overrides the video width for this render. |
| `--height` | scene `video.height` | Overrides the video height. |
| `--fps` | scene `video.fps` | Overrides the frame rate. |
| `--frames` | scene `video.frames` | Overrides the transition frames per leg. |
| `--first_hold` | scene `video.first_hold` (10) | Copies of the first frame at the start. |
| `--last_hold` | scene `video.last_hold` (10) | Copies of the last frame at the end. |

The overrides apply to this render only; the scene file is not changed.

```bash
vexy-stax video scene.json --out morph.mp4
vexy-stax video scene.json --engine pygfx --fps 24 --first_hold 0 --last_hold 0 --out preview.mp4
```

## `overlay`

Composite the slides into one flat PNG with Pillow.

```bash
vexy-stax overlay SCENE [--out flat.png]
```

The canvas is as wide as the widest image and as tall as the tallest. Each image is centred horizontally and aligned to the bottom, and the images are alpha-composited from slide 0 upward. No engine is involved, so this works without a GPU, Blender or a browser.

## `engines`

```bash
vexy-stax engines
```

Prints `Available engines:` followed by the engines whose dependency probe succeeds, for example `blender, playwright, pygfx`. See [Installation](installation.md#verify-the-install) for what each probe checks.

## Engine defaults and errors

| Command | Default engine |
|---------|----------------|
| `render` | `pygfx` |
| `video` | `blender` |

- An unknown engine name prints `Unknown engine 'NAME'. Registered: blender, playwright, pygfx` and writes nothing.
- An engine that raises `NotImplementedError` prints `Engine 'NAME' not ready:` with the reason.
- Other errors, such as a missing transition or a missing ffmpeg, end with a Python traceback that names the cause.

## Environment variables

| Variable | Effect |
|----------|--------|
| `VEXY_STAX_TURBO=1` | The Blender engine renders with Eevee and 8 samples instead of Cycles with 16 samples. Use it for fast previews. |

```bash
VEXY_STAX_TURBO=1 vexy-stax render scene.json --engine blender --out preview.png
```
