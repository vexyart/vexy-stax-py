# Vexy Stax PY - Implementation Plan

**Purpose**: Playwright-based browser automation and CLI for vexy-stax-js web application

---

## Core Objectives

1. **Browser Automation**: Control vexy-stax-js through Playwright
2. **CLI Interface**: Fire-based command-line interface for scripting
3. **Video Export**: Capture animations and export as video files
4. **Test Image Generation**: Create test assets for development

---

## Architecture Overview

```
vexy-stax-py/
├── src/vexy_stax/
│   ├── __init__.py           # Package init
│   ├── _version.py           # Auto-generated version
│   ├── cli.py                # Fire CLI entry point
│   ├── browser.py            # Playwright browser automation
│   ├── capture.py            # Video/screenshot capture
│   └── test_images.py        # Test image generation
├── examples/
│   ├── basic_usage.py        # Simple automation example
│   ├── video_export.py       # Animation + export
│   └── batch_processing.py   # Multiple configs
└── scripts/
    └── install_playwright.sh # Setup helper
```

---

## Phase 1: Core Browser Automation

### 1.1 Playwright Integration

**Goal**: Launch and control vexy-stax-js in headless/headed browser

**Implementation**:
```python
# src/vexy_stax/browser.py
class VexyStaxBrowser:
    def __init__(self, headless=False, url=None):
        """Initialize Playwright browser with vexy-stax-js"""

    async def launch(self):
        """Start browser and navigate to app"""

    async def load_images(self, image_paths: list[str]):
        """Upload images to the app"""

    async def set_z_spacing(self, spacing: int):
        """Adjust Z-spacing via Tweakpane"""

    async def set_camera_mode(self, mode: str):
        """Switch camera mode (perspective/ortho/isometric)"""

    async def apply_material(self, preset: str):
        """Apply material preset"""

    async def export_png(self, scale: int = 1):
        """Trigger PNG export"""

    async def close(self):
        """Clean up browser"""
```

**Dependencies**:
- `playwright>=1.40.0` (browser automation)
- `asyncio` (async operations)

**Testing**:
- Can launch browser
- Can navigate to local/remote URL
- Can interact with Tweakpane controls
- Can trigger exports

---

### 1.2 Image Loading Automation

**Goal**: Programmatically load images into the 3D scene

**Approach**:
- Use Playwright file chooser API
- Wait for images to load (check imageStack via console API)
- Verify all images loaded successfully

**Implementation**:
```python
async def load_images(self, image_paths: list[str]):
    # Find file input element
    file_input = await self.page.query_selector('#image-input')

    # Set files
    await file_input.set_input_files(image_paths)

    # Wait for images to appear in stack
    await self.page.wait_for_function(
        f"window.vexyStax.getImageStack().length === {len(image_paths)}"
    )
```

---

## Phase 2: Fire CLI Interface

### 2.1 CLI Structure

**Goal**: Simple command-line interface using Fire

**Commands**:
```bash
# Generate test images
vexy-stax generate-test

# Launch browser with images
vexy-stax launch --images layer*.png

# Export PNG from config
vexy-stax export config.json --scale 2x

# Capture animation video
vexy-stax animate config.json --duration 3s --output video.webm
```

**Implementation**:
```python
# src/vexy_stax/cli.py
import fire

class VexyStaxCLI:
    def generate_test(self, output_dir="test-img", count=3):
        """Generate colored test images"""

    def launch(self, images=None, url=None, headless=False):
        """Launch browser with optional images"""

    def export(self, config, scale=1, output=None):
        """Export PNG from JSON config"""

    def animate(self, config, duration="3s", output="animation.webm"):
        """Capture animation video"""

def main():
    fire.Fire(VexyStaxCLI)
```

**Entry Point** (pyproject.toml):
```toml
[project.scripts]
vexy-stax = "vexy_stax.cli:main"
```

---

### 2.2 Configuration Support

**Goal**: Load/save configurations for automation

**JSON Schema**:
```json
{
  "images": ["layer1.png", "layer2.png", "layer3.png"],
  "settings": {
    "zSpacing": 100,
    "bgColor": "#000000",
    "cameraMode": "perspective",
    "cameraFOV": 75,
    "materialPreset": "Glossy Photo"
  },
  "export": {
    "scale": 2,
    "format": "png"
  }
}
```

---

## Phase 3: Video Capture System

### 3.1 Animation Recording

**Goal**: Capture the "hero shot" animation as video

**Implementation**:
```python
# src/vexy_stax/capture.py
class VideoCapture:
    def __init__(self, page, fps=60):
        self.page = page
        self.fps = fps

    async def record_animation(self, duration_seconds: float):
        """Record animation frames"""
        frames = []
        frame_count = int(duration_seconds * self.fps)

        # Trigger animation via console API
        await self.page.evaluate("window.vexyStax.playAnimation()")

        # Capture frames
        for i in range(frame_count):
            screenshot = await self.page.screenshot()
            frames.append(screenshot)
            await asyncio.sleep(1 / self.fps)

        return frames

    def encode_video(self, frames, output_path: str, codec="libvpx-vp9"):
        """Encode frames to WebM using ffmpeg"""
```

**Dependencies**:
- `ffmpeg-python>=0.2.0` (video encoding)
- Or use `opencv-python` for frame encoding

---

### 3.2 Screenshot Capture

**Goal**: Capture high-resolution screenshots

**Implementation**:
```python
async def capture_screenshot(self, scale: int = 1):
    """Capture viewport at specified scale"""
    # Set device scale factor
    await self.page.set_viewport_size(
        width=1920 * scale,
        height=1080 * scale,
        device_scale_factor=scale
    )

    screenshot = await self.page.screenshot(type='png')
    return screenshot
```

---

## Phase 4: Test Image Generation

### 4.1 Colored Layers

**Goal**: Generate test images for development

**Already Implemented**: `create_test_images.py`

**Keep As Is**: This functionality is solid and useful

---

## Dependencies

### Required
```toml
dependencies = [
    "playwright>=1.40.0",      # Browser automation
    "fire>=0.6.0",             # CLI interface
    "pillow>=11.0.0",          # Image generation
    "ffmpeg-python>=0.2.0",    # Video encoding (optional)
]
```

### Optional
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-playwright>=0.4.0",
]
```

---

## Build & Deployment

### Build Script (`build.sh`)
```bash
#!/bin/bash
set -e

echo "Building vexy-stax-py..."

# Install Playwright browsers
python -m playwright install chromium

# Build package
uv build

# Run tests
pytest -v

echo "Build complete!"
```

### Installation

```bash
# Install package
pip install vexy-stax

# Install Playwright browsers (first time only)
playwright install chromium
```

---

## Usage Examples

### Example 1: Generate and View Test Images
```python
from vexy_stax import VexyStaxBrowser
from vexy_stax.test_images import generate_test_images
import asyncio

async def main():
    # Generate test images
    generate_test_images("test-img", count=3)

    # Launch browser and load them
    browser = VexyStaxBrowser()
    await browser.launch()
    await browser.load_images(["test-img/layer1.png",
                               "test-img/layer2.png",
                               "test-img/layer3.png"])

    # Apply material
    await browser.apply_material("Glossy Photo")

    # Export
    await browser.export_png(scale=2)

    await browser.close()

asyncio.run(main())
```

### Example 2: CLI Usage
```bash
# Generate test images
vexy-stax generate-test

# Launch with images
vexy-stax launch --images test-img/*.png

# Export from config
vexy-stax export config.json --scale 2

# Capture animation
vexy-stax animate config.json --output hero-shot.webm
```

---

## Testing Strategy

### Unit Tests
- Test image generation (existing tests)
- Test configuration parsing
- Test CLI argument parsing

### Integration Tests
- Launch browser successfully
- Load images via automation
- Trigger exports
- Verify exported files

### E2E Tests
- Full workflow: generate → launch → configure → export
- Animation capture workflow
- Batch processing multiple configs

---

## Future Enhancements

1. **Batch Processing**: Process multiple configurations in parallel
2. **Cloud Support**: Deploy to serverless (AWS Lambda + Playwright)
3. **GUI Wrapper**: Optional Tkinter/Qt GUI for non-CLI users
4. **Plugin System**: Allow custom automation scripts
5. **Performance Monitoring**: Track render times, export quality

---

## Migration from Current State

### Remove
- ❌ `validate_output.py` (validation is not core objective)
- ❌ `tests/test_validate_output.py` (validation tests)
- ❌ Validation-focused README sections

### Rename
- ✅ `create_test_images.py` → `test_images.py` (keep functionality)

### Add
- ✅ `browser.py` (Playwright automation)
- ✅ `cli.py` (Fire CLI)
- ✅ `capture.py` (Video/screenshot capture)
- ✅ `examples/` directory (usage examples)
- ✅ `build.sh` (build script)

---

## Timeline

- **Phase 1**: 2-3 days (Browser automation core)
- **Phase 2**: 1-2 days (CLI interface)
- **Phase 3**: 2-3 days (Video capture)
- **Phase 4**: Already done (Test images)

**Total**: ~1 week for MVP implementation

---

**Status**: Planning phase complete. Ready for implementation.
