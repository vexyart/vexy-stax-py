---
this_file: README.md
---

# Vexy Stax PY

> Headless Python renderer for vexy-stax JSON scenes → PNG stills and MP4/MOV animations.

## Current Status

### ✅ Working Now
- **pygfx headless rendering** (default): Real GPU rendering via Metal/Vulkan/DirectX (113/117 tests)
- **PNG export**: High-quality stills with supersampling (1×, 2×, 4×)
- **Video export**: MP4/MOV hero-shot animations with codec fallback
- **CLI backend selection**: `--backend=pygfx` (default) or `--backend=playwright`
- **GPU diagnostics**: `vexy-stax doctor` command for troubleshooting

### 📦 Browser Backend (Optional)
- Playwright browser automation available via `pip install vexy-stax[browser]`
- Use `--backend=playwright` for pixel-perfect match to vexy-stax-js web UI

## Quick Start

### Pygfx headless rendering (recommended)
```bash
# 1. Install the package
uv sync

# 2. Check GPU availability
uv run vexy-stax doctor

# 3. Create test scene
uv run vexy-stax-create-test  # generates test-img/layer123.json

# 4. Render PNG with GPU (pygfx is now default)
uv run vexy-stax render test-img/layer123.json output.png

# 5. Export hero-shot video
uv run vexy-stax animate test-img/layer123.json hero.mp4
```

## Commands

### `vexy-stax doctor`
Check GPU availability and get platform-specific advice:
```bash
uv run vexy-stax doctor
```
Output shows adapter name, backend (Metal/Vulkan/DirectX), and recommendations if GPU unavailable.

### `vexy-stax render`

**Pygfx backend (default):**
```bash
uv run vexy-stax render scene.json output.png \
  --width=1920 \
  --height=1080 \
  --scale=2  # 1, 2, or 4 for supersampling
```

**Playwright backend (optional, requires `vexy-stax[browser]`):**
```bash
uv run vexy-stax render scene.json output.png \
  --backend=playwright \
  --url=http://localhost:5173/vexy-stax-js/
```

### `vexy-stax animate`

**Pygfx backend (default, exports video):**
```bash
uv run vexy-stax animate scene.json hero.mp4 \
  --width=1920 \
  --height=1080 \
  --fps=30 \
  --duration=1.5 \
  --hold=1.0
```
Exports MP4 (H.264) or MOV (ProRes) based on output extension.

**Playwright backend (optional, preview only):**
```bash
uv run vexy-stax animate ./layers --backend=playwright
```
Plays animation in headless browser but does not export video.

### `vexy-stax compare`
Compare two images and report visual similarity:
```bash
uv run vexy-stax compare pygfx_render.png js_reference.png

# With diff visualization
uv run vexy-stax compare pygfx_render.png js_reference.png --diff-output=diff.png
```
Shows MAE, pixel match ratio, and pass/fail status.

### `vexy-stax version`
Show package version and backend capabilities.

### `vexy-stax-create-test`
Generate test images and JSON scene for quick imports.

## Scene JSON Format

The Python renderer reads JSON scenes exported from vexy-stax-js:

```json
{
  "version": "1.0",
  "params": {
    "zSpacing": 150,
    "bgColor": "#1a1a2e",
    "transparentBg": false,
    "cameraMode": "perspective",
    "cameraFov": 75,
    "cameraZoom": 1.0
  },
  "camera": {
    "position": { "x": 200, "y": 150, "z": 400 }
  },
  "settings": {
    "viewpoint": "beauty",
    "material": "glossy",
    "materialThickness": 5,
    "floorOpacity": 0.3,
    "ambientMode": false
  },
  "images": [
    {
      "filename": "back.png",
      "width": 800,
      "height": 600,
      "data": "data:image/png;base64,..."
    }
  ]
}
```

**Key fields:**
- `params`: Scene parameters (spacing, background, camera settings)
- `camera.position`: Camera location in 3D space
- `settings`: Visual settings (material preset, viewpoint)
- `images`: Base64-encoded image layers (back to front order)

## Visual Regression Testing

Cross-renderer comparison thresholds:
- **MAE < 35**: Average pixel difference under ~14% of 255
- **pixel_match_ratio > 0.35**: At least 35% pixels within tolerance

These thresholds account for shader implementation differences between pygfx and Three.js while catching significant regressions like missing layers or wrong geometry.

```python
from vexy_stax.image_comparison import compare_images

result = compare_images("pygfx_render.png", "js_reference.png")
print(result.summary())  # "PASS: MAE=28.50, match=46.2%, max_diff=180"
```

## Development

### Running tests
```bash
uvx ruff check --fix . && uvx ruff format . && uvx hatch test
```

### Module structure
- `vexy_stax.cli` – Fire CLI commands
- `vexy_stax.loader` – JSON scene parsing with pydantic
- `vexy_stax.render_pipeline` – End-to-end pygfx rendering
- `vexy_stax.renderer.*` – Canvas, camera, materials, export
- `vexy_stax.gpu_doctor` – GPU diagnostics
- `vexy_stax.image_comparison` – Visual regression utilities

## Requirements

- Python 3.12+
- GPU with Metal (macOS), Vulkan (Linux), or DirectX 12 (Windows)
- FFmpeg for video export

### Software Rendering Fallback (CI/Docker)

When no GPU is available, wgpu can use CPU-based software rendering:

**LLVMpipe (Linux/Mesa):**
```bash
# Install Mesa with LLVMpipe
sudo apt install mesa-vulkan-drivers

# Force software adapter
export WGPU_ADAPTER_NAME="llvmpipe"
uv run vexy-stax render scene.json output.png --backend=pygfx
```

**SwiftShader (Cross-platform):**
```bash
# Set adapter name to SwiftShader
export WGPU_ADAPTER_NAME="SwiftShader Device"
```

**Verify adapter:**
```bash
uv run vexy-stax doctor
# Shows "llvmpipe (LLVM 15.0.6)" or similar for software rendering
```

Note: Software rendering is significantly slower than GPU but works in headless CI environments.

**GitHub Actions example:**
```yaml
jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Mesa
        run: sudo apt-get install -y mesa-vulkan-drivers
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Render with software fallback
        env:
          WGPU_ADAPTER_NAME: llvmpipe
        run: |
          uv run vexy-stax doctor  # Verify llvmpipe detected
          uv run vexy-stax render scene.json output.png --backend=pygfx
```

### FFmpeg Installation

Video export requires FFmpeg with H.264 support:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

**Verify installation:**
```bash
ffmpeg -version
```

## License
MIT
