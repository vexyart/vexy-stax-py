---
title: Installation
nav_order: 6
---

# Installation

## Requirements

- **Python 3.12+**
- **uv** (recommended) or pip

Optional engine prerequisites:

| Engine | Prerequisite | Notes |
|--------|-------------|-------|
| pygfx | `wgpu`-capable GPU driver | Usually auto-satisfied; works on CPU fallback too |
| blender | `blender` binary on PATH | Blender 4.x recommended |
| playwright | `playwright` Python package + Chromium | Install separately |

---

## Install with uv (recommended)

```bash
# From source in the vexy-stax-py directory
uv venv --python 3.12 --clear
uv sync
```

This creates a virtual environment and installs all dependencies including `pygfx`.

To install into an existing project:

```bash
uv add vexy-stax
```

---

## Install with pip

```bash
pip install vexy-stax
```

Or from source:

```bash
pip install -e .
```

---

## Verify the install

```bash
vexy-stax engines
```

Expected output when pygfx is available:

```
Available engines: blender, pygfx
```

(blender appears only if the `blender` binary is on PATH; playwright only if installed.)

---

## Installing optional engines

### Blender

Download Blender from [blender.org](https://blender.org) and ensure the `blender` binary is on your PATH:

```bash
# macOS example
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
blender --version
```

vexy-stax invokes Blender as a subprocess (`blender --background --python _blender_render.py`). Blender 4.x is recommended; Blender 3.6 LTS also works.

### Playwright

```bash
uv add playwright
python -m playwright install chromium
```

Or with pip:

```bash
pip install playwright
playwright install chromium
```

The playwright engine drives headless Chromium to render via the vexy-stax-js browser build. It requires the vexy-stax-js dist bundle to be built.

---

## The bundled font

vexy-stax-py ships a bundled caption font inside the wheel:

```
src/vexy_stax/fonts/vexy-stax.ttf   # Zalando Sans Expanded
src/vexy_stax/fonts/OFL.txt         # SIL Open Font License
```

This font is automatically used for captions when no explicit `font` is set in the scene. The JS package matches it with the Google Font **"Zalando Sans"** at `wdth 125 / wght 500`.

You can locate the bundled font path from Python:

```python
from vexy_stax.geometry import default_font_path
print(default_font_path())  # Path to vexy-stax.ttf, or None if not installed
```

---

## ffmpeg (for pygfx video)

The pygfx engine renders video by writing individual frames then compiling them with ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt install ffmpeg
```

ffmpeg is not required for still renders or for the blender video engine.

---

## Running tests

```bash
uv run pytest -q
```

Engine-specific tests are gated by pytest marks (`@pytest.mark.blender`, `@pytest.mark.playwright`) and are skipped automatically when the engine is not available.

For a full functional test including actual renders:

```bash
bash test.sh
```

This runs lint, type checks, and a functional render of the bundled `testdata/airbl-lores/` scene with each available engine.
