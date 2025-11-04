# Vexy Stax PY - Quick Start

Python automation for vexy-stax-js. Get started in 3 minutes.

## Install

```bash
pip install vexy-stax

# Or from source
git clone https://github.com/vexyart/vexy-stax-py.git
cd vexy-stax-py
pip install -e .
```

## Prerequisites

Start the vexy-stax-js dev server first:

```bash
cd ../vexy-stax-js
npm install
npm run dev
# Server runs at http://localhost:5173/vexy-stax-js/
```

## Basic Usage

### 1. Generate Test Images

```bash
vexy-stax-create-test
# Creates test-img/ folder with 3 colored PNG layers
```

### 2. Launch Browser with Images

```bash
# Open browser with test images
vexy-stax launch --images test-img/

# Or load a saved config
vexy-stax launch --images config.json

# Headless mode
vexy-stax launch --images test-img/ --headless
```

### 3. Automate Animation

```bash
# Play animation and export (future: video recording)
vexy-stax animate --images test-img/ --duration 2 --hold 1.5

# Use custom config
vexy-stax animate --images my-config.json --duration 1.5
```

## Python API

For programmatic control:

```python
from vexy_stax import VexyStaxBrowser

# Create browser instance
browser = VexyStaxBrowser(url="http://localhost:5173/vexy-stax-js/")

try:
    # Launch browser
    browser.launch()

    # Load images
    browser.load_images(["layer1.png", "layer2.png", "layer3.png"])

    # Or load config
    browser.load_config("config.json")

    # Play animation
    browser.play_animation(duration=2.0, hold_time=1.5)

    # Export PNG
    browser.export_png(scale=2, output_path="output.png")

    # Get stats
    stats = browser.get_stats()
    print(f"Loaded {stats['imageCount']} images")

finally:
    browser.close()
```

## Common Tasks

### Export High-Resolution Renders

```python
from vexy_stax import VexyStaxBrowser

browser = VexyStaxBrowser()
try:
    browser.launch()
    browser.load_config("my-stack.json")

    # Export at 4x resolution (high quality)
    browser.export_png(scale=4, output_path="render-4x.png")
finally:
    browser.close()
```

### Batch Processing

```python
from vexy_stax import VexyStaxBrowser
from pathlib import Path

configs = Path("configs").glob("*.json")
browser = VexyStaxBrowser(headless=True)

try:
    browser.launch()

    for config in configs:
        browser.load_config(str(config))
        output = f"renders/{config.stem}.png"
        browser.export_png(scale=2, output_path=output)
        print(f"✓ Rendered {output}")
finally:
    browser.close()
```

### Test Automation

```python
from vexy_stax import VexyStaxBrowser

def test_image_loading():
    browser = VexyStaxBrowser(headless=True)
    try:
        browser.launch()
        browser.load_images(["test1.png", "test2.png"])

        stats = browser.get_stats()
        assert stats['imageCount'] == 2, "Should load 2 images"

        print("✓ Test passed")
    finally:
        browser.close()

test_image_loading()
```

## CLI Options

### launch
```bash
vexy-stax launch [OPTIONS]

Options:
  --images PATH    Path to folder with PNG files or JSON config
  --url URL        Dev server URL (default: http://localhost:5173/vexy-stax-js/)
  --headless       Run in headless mode
```

### animate
```bash
vexy-stax animate [OPTIONS]

Options:
  --images PATH    Path to folder with PNG files or JSON config (required)
  --output PATH    Output file (default: animation.webm)
  --url URL        Dev server URL
  --duration FLOAT Animation duration in seconds (default: 1.5)
  --hold FLOAT     Hold time at hero position (default: 1.0)
```

## Error Handling

The library provides clear error messages:

```python
from vexy_stax import VexyStaxBrowser

browser = VexyStaxBrowser()

try:
    browser.launch()
    browser.load_config("missing.json")
except RuntimeError as e:
    print(e)
    # load_config: Config file not found: missing.json
    # Make sure the file exists and the path is correct.
```

All methods validate inputs and provide actionable error messages.

## Requirements

- Python 3.12+
- Playwright (automatically installs Chromium)
- Running vexy-stax-js dev server

## Install Playwright Browsers

First time only:

```bash
playwright install chromium
```

## Tips

- Always start the dev server before using the CLI
- Use `--headless` for CI/CD and automation scripts
- Config JSON files include embedded image data (base64)
- Polling-based image loading waits up to 5 seconds
- All file paths are validated before operations

## Need More?

- Full documentation: [README.md](README.md)
- Web app: [vexy-stax-js](../vexy-stax-js/)
- API details: See docstrings in `browser.py`

## Troubleshooting

**"Cannot connect to http://localhost:5173"**
→ Start the dev server: `cd ../vexy-stax-js && npm run dev`

**"Browser not launched"**
→ Call `browser.launch()` before other methods

**"Timeout waiting for images to load"**
→ Images may be too large (>50MB) or failed to load. Check console logs.
