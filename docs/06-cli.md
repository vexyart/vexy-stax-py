---
title: CLI Usage
nav_order: 7
---

# CLI Usage

The `vexy-stax` command is a `fire` + `rich` CLI implemented in `src/vexy_stax/cli.py`. All subcommands are methods of the `Stax` class.

## Overview

```
vexy-stax COMMAND [OPTIONS]

Commands:
  dir2scene   Generate a scene JSON from a directory of images
  render      Render a single still (expanded or compact)
  video       Render the transition to a video file
  overlay     Pure-Pillow flat composite (no 3D engine)
  engines     List available engines
```

---

## `dir2scene`

Scan a directory of images, auto-detect dimensions, and write a scene JSON.

```bash
vexy-stax dir2scene DIRECTORY [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `DIRECTORY` | Directory containing PNG/JPG/JPEG/WEBP images |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--out` | path | `scene.json` | Output path for the scene JSON |
| `--view` | string | `expanded` | Initial view (`expanded` or `compact`) |
| `--width` | int | auto | Override canvas width (default: first image width) |
| `--height` | int | auto | Override canvas height (default: first image height) |
| `--gap` | float | auto | Plate gap in points (default: ≈38% of scene width) |
| `--distance` | str/float | `"100%"` | Camera distance (absolute or `"P%"`) |
| `--angle` | float | `60.0` | Azimuth degrees for expanded camera |
| `--elevation` | float | `0.0` | Elevation degrees for expanded camera |
| `--fov` | float | `39.6` | Horizontal FOV in degrees |
| `--background` | string | `"#ffffff"` | Canvas background color |
| `--floor-color` | string | `"#f2f2f2"` | Floor color |
| `--floor-opacity` | float | `1.0` | Floor opacity |
| `--floor-reflectivity` | float | `0.5` | Floor reflection strength |
| `--transition-kind` | string | `null` | Add a transition block: `expand`, `collapse`, `expand_collapse`, `collapse_expand` |
| `--transition-duration` | float | `3.0` | Seconds per transition leg |
| `--transition-wait` | float | `1.0` | Hold seconds at far end |
| `--transition-fps` | int | `30` | Frames per second |
| `--transition-easing` | string | `"easeInOutCubic"` | Easing curve |
| `--reverse` | bool | `false` | Reverse the order of images (front-to-back → back-to-front) |
| `--captions` | bool | `true` | Auto-generate captions from filenames |
| `--juicy` | bool | `false` | Enable Python color correction |

### Caption auto-generation

When `--captions` is enabled (default), `dir2scene` derives caption text from each filename:

1. Strips any common prefix shared by all files.
2. Strips leading/trailing digits and separators.
3. Replaces hyphens/underscores with spaces.
4. Title-cases the result.

For example, `airbl-020-source.png` → common prefix `airbl-` stripped → `020-source` → strip leading digits → `source` → `"Source"`.

### Examples

```bash
# Basic: scan assets/, write scene.json
vexy-stax dir2scene assets/ --out scene.json

# With transition
vexy-stax dir2scene assets/ --out scene.json \
  --transition-kind expand_collapse \
  --transition-duration 3.0 \
  --transition-wait 1.0

# 4K, angled 45°, no captions
vexy-stax dir2scene assets/ --out scene.json \
  --width 3840 --height 2160 \
  --angle 45 \
  --captions false

# Reverse layer order (if your folder is front-to-back)
vexy-stax dir2scene assets/ --out scene.json --reverse
```

---

## `render`

Render a single still image in the specified view.

```bash
vexy-stax render SCENE [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `SCENE` | Path to the scene JSON file |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--view` | string | `expanded` | Which view to render (`expanded` or `compact`) |
| `--engine` | string | `pygfx` | Engine to use (`blender`, `pygfx`, `playwright`) |
| `--out` | path | `out.png` | Output PNG path |

### Examples

```bash
# Expanded hero shot with pygfx (fast)
vexy-stax render scene.json --view expanded --engine pygfx --out beauty.png

# Compact stack with blender (quality)
vexy-stax render scene.json --view compact --engine blender --out stack.png

# Default engine (pygfx), expanded view
vexy-stax render scene.json --out hero.png
```

---

## `video`

Render the scene's transition to a video file. Requires a `transition` block in the scene JSON.

```bash
vexy-stax video SCENE [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `SCENE` | Path to the scene JSON file |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--engine` | string | `blender` | Engine to use (`blender`, `pygfx`, `playwright`) |
| `--out` | path | `out.mp4` | Output MP4 path |

### Examples

```bash
# Blender video (default, highest quality)
vexy-stax video scene.json --out morph.mp4

# pygfx video (faster, good quality)
vexy-stax video scene.json --engine pygfx --out morph.mp4

# Playwright video (JS-renderer reference)
vexy-stax video scene.json --engine playwright --out morph.mp4
```

---

## `overlay`

Render a flat 2D composite of all slides using Pillow — no 3D engine required. Useful for quick previews.

```bash
vexy-stax overlay SCENE [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--out` | path | `flat.png` | Output PNG path |

### Example

```bash
vexy-stax overlay scene.json --out preview.png
```

---

## `engines`

List which engines are available in the current environment.

```bash
vexy-stax engines
```

Output example:

```
Available engines: pygfx
```

Or if blender and playwright are also installed:

```
Available engines: blender, pygfx, playwright
```

If an engine's dependency is missing, it is excluded from the list. Attempting to use an unavailable engine prints an actionable error message rather than crashing.

---

## Engine defaults

| Command | Default engine | Rationale |
|---------|---------------|-----------|
| `render` | `pygfx` | Fast GPU-accelerated off-screen render |
| `video` | `blender` | Highest quality ray-traced output |

---

## Environment variable

Set `VEXY_STAX_TURBO=1` to use Blender's Eevee renderer instead of Cycles (faster but lower quality, mainly for testing):

```bash
VEXY_STAX_TURBO=1 vexy-stax render scene.json --engine blender --out fast.png
```
