# Installation

## Requirements

- Python 3.12 or newer (`requires-python = ">=3.12"`).
- [uv](https://docs.astral.sh/uv/) (recommended) or pip.

Installing the package also installs its Python dependencies: `fire`, `rich`, `pillow`, `numpy`, `pydantic` (v2), `opencv-python-headless`, `pygfx`, `pylinalg` and `playwright`. Some engines need more than a Python package; see [Engine prerequisites](#engine-prerequisites).

## Install from PyPI

The package is published as `vexy-stax`:

```bash
pip install vexy-stax
```

or, inside a uv project:

```bash
uv add vexy-stax
```

Both install the `vexy-stax` command. You can also run the CLI as a module:

```bash
python -m vexy_stax engines
```

## Install from a checkout

Use this when you want to change the code or run the tests.

1. Clone the repository:

    ```bash
    git clone https://github.com/vexyart/vexy-stax-py.git
    cd vexy-stax-py
    ```

2. Create the virtual environment and install the package with its development dependencies:

    ```bash
    uv venv --python 3.12
    uv sync
    ```

3. Run the CLI from the environment:

    ```bash
    uv run vexy-stax engines
    ```

The version is derived from the git tags by hatch-vcs, so a checkout needs its git history (not a bare source export) to report a proper version.

## Verify the install

```bash
vexy-stax engines
```

The command prints the engines whose dependencies are present, in registration order, for example:

```text
Available engines: blender, playwright, pygfx
```

The check is cheap and does not import the engines:

| Engine | Listed when |
|--------|-------------|
| `blender` | a `blender` binary is on `PATH` |
| `pygfx` | the `pygfx` Python package is importable |
| `playwright` | the `playwright` Python package is importable |

Because `pygfx` and `playwright` are package dependencies, both are normally listed. Being listed does not guarantee the engine can render; the next section lists what each one still needs.

## Engine prerequisites

### pygfx

pygfx renders off-screen through WGPU and needs a working WGPU backend (Metal on macOS, Vulkan or DirectX elsewhere). Stills need nothing else.

For video, pygfx writes a PNG sequence and assembles it with **ffmpeg**, which must be on `PATH`:

```bash
brew install ffmpeg        # macOS
sudo apt install ffmpeg    # Debian/Ubuntu
```

Without it the video command fails with `ffmpeg not found on PATH`.

### Blender

vexy-stax runs Blender as a separate process. Install Blender and make the `blender` binary reachable. The engine looks for it in this order:

1. `blender` on `PATH`
2. `/opt/homebrew/bin/blender`
3. `/Applications/Blender.app/Contents/MacOS/Blender`

On macOS, `brew install --cask blender` works. To put the app bundle's binary on `PATH`:

```bash
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"
blender --version
```

`vexy-stax engines` only checks `PATH`, so a Blender found through the fallback paths still renders but is not listed.

Blender video also assembles frames with ffmpeg.

### Playwright

The Playwright engine drives headless Chromium. Install the browser once:

```bash
python -m playwright install chromium
```

It also needs the **built vexy-stax-js bundle**. The engine expects a `vexy-stax-js` checkout next to the `vexy-stax-py` checkout and loads `vexy-stax-js/dist/vexy-stax.element.js` from it. If the bundle is missing, the engine tells you how to build it:

```bash
cd ../vexy-stax-js && npm install && npm run build
```

In practice this engine is meant for a development checkout of both repositories, not for a plain `pip install`.

Playwright video also assembles frames with ffmpeg.

## The bundled caption font

The wheel ships a caption font:

```text
vexy_stax/fonts/vexy-stax.ttf   # Zalando Sans Expanded
vexy_stax/fonts/OFL.txt         # SIL Open Font License
```

Captions use it whenever the scene sets no `font`. To find it from Python:

```python
from vexy_stax.geometry import default_font_path

print(default_font_path())  # Path to vexy-stax.ttf, or None if missing
```

## Run the tests

From a checkout:

```bash
uv run pytest -q
```

The default selection excludes tests marked `slow`. Tests marked `blender`, `pygfx` or `playwright` skip themselves when their engine is unavailable.
