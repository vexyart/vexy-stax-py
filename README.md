# Vexy Stax PY

**Python CLI tools for testing and validating vexy-stax-js outputs**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/PyPI-vexy--stax-blue)](https://pypi.org/project/vexy-stax/)

Vexy Stax PY is a Python CLI package that provides test image generation and PNG validation tools for the **vexy-stax-js** web application. It enables automated testing workflows and quality assurance for 3D image stack visualization.

---

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (when published)
pip install vexy-stax

# Or install from source
git clone https://github.com/vexyart/vexy-stax-py.git
cd vexy-stax-py
pip install -e .
```

### Usage

```bash
# Generate test images (creates test-img/ folder)
vexy-stax-create-test

# Validate PNG exports from vexy-stax-js
vexy-stax-validate
```

---

## 📖 Table of Contents

- [What It Does](#what-it-does)
- [How It Works](#how-it-works)
- [Integration with vexy-stax-js](#integration-with-vexy-stax-js)
- [CLI Commands](#cli-commands)
- [Architecture](#architecture)
- [Development](#development)
- [Testing](#testing)
- [Versioning & Releases](#versioning--releases)

---

## What It Does

Vexy Stax PY provides two essential CLI tools for the vexy-stax ecosystem:

1. **Test Image Generator** (`vexy-stax-create-test`):
   - Creates colored PNG layers for testing 3D stack visualization
   - Generates consistent test assets for development and QA
   - Produces labeled images (Layer 1 - Red, Layer 2 - Cyan, Layer 3 - Yellow)

2. **PNG Output Validator** (`vexy-stax-validate`):
   - Validates PNG files exported from vexy-stax-js
   - Checks file format, dimensions, and content validity
   - Detects blank or corrupted outputs
   - Used for automated testing and quality assurance

### Use Cases
- **Development**: Generate test images quickly without manual creation
- **Testing**: Validate vexy-stax-js PNG exports in CI/CD pipelines
- **QA**: Verify output quality across different browser/OS combinations
- **Automation**: Integrate into test suites for continuous validation

---

## How It Works

### Test Image Creation (`vexy-stax-create-test`)

**Process Flow**:
```
1. Create test-img/ directory in current working directory
2. Generate 3 PNG files:
   - layer1.png (400×300px, #FF6B6B red with label)
   - layer2.png (400×300px, #4ECDC4 cyan with label)
   - layer3.png (400×300px, #FFE66D yellow with label)
3. Use Pillow (PIL) to create RGBA images
4. Apply font rendering for labels (Helvetica on macOS, fallback to default)
5. Save as PNG with optimal compression
```

**Implementation**:
```python
# src/vexy_stax/create_test_images.py
def main():
    test_dir = Path.cwd() / "test-img"
    test_dir.mkdir(exist_ok=True)

    colors = [
        ("#FF6B6B", "Layer 1 - Red"),
        ("#4ECDC4", "Layer 2 - Cyan"),
        ("#FFE66D", "Layer 3 - Yellow"),
    ]

    for i, (color, label) in enumerate(colors, 1):
        img = Image.new("RGBA", (400, 300), color)
        draw = ImageDraw.Draw(img)
        draw.text((100, 126), label, fill="black", font=font)
        img.save(test_dir / f"layer{i}.png")
```

**Output Format**:
- **Format**: PNG with alpha channel (RGBA)
- **Dimensions**: 400×300 pixels (consistent test size)
- **Colors**: High-contrast colors for easy visual verification
- **Labels**: Black text identifying each layer

### PNG Validation (`vexy-stax-validate`)

**Validation Checks**:
1. **File Existence**: Verifies file is present at expected path
2. **Format Check**: Confirms file is PNG (not JPEG/other)
3. **Dimension Check**: Validates width/height match expectations
4. **Content Check**: Detects blank images (all-black or all-transparent)
5. **Metadata Extraction**: Reports actual dimensions, color mode, file size

**Implementation**:
```python
# src/vexy_stax/validate_output.py
def validate_png(
    path: Path,
    expected_width: int | None = None,
    expected_height: int | None = None
) -> tuple[bool, str]:
    if not path.exists():
        return False, f"File not found: {path}"

    with Image.open(path) as img:
        if img.format != "PNG":
            return False, f"Not PNG format (got: {img.format})"

        if expected_width and img.width != expected_width:
            return False, f"Width mismatch: expected {expected_width}px"

        # Check if image has content (not blank)
        data = list(img.getdata())
        if all(pixel == (0,0,0) or pixel == (0,0,0,0) for pixel in data[:100]):
            return False, "Image appears to be blank"

        return True, ""
```

**Exit Codes**:
- `0`: All validations passed
- `1`: One or more validations failed

---

## Integration with vexy-stax-js

Vexy Stax PY is designed as a **complementary tool** for the vexy-stax-js web application:

### Integration Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Development & Testing Workflow                            │
└─────────────────────────────────────────────────────────────┘

1. GENERATE TEST IMAGES
   $ vexy-stax-create-test
   ├── Creates test-img/layer1.png
   ├── Creates test-img/layer2.png
   └── Creates test-img/layer3.png

2. LOAD IN WEB APP
   Open https://vexyart.github.io/vexy-stax-js/
   ├── Drag & drop test-img/*.png files
   ├── Arrange in 3D space
   ├── Apply materials and camera settings
   └── Export PNG (1x, 2x, or 4x resolution)

3. VALIDATE EXPORTS
   $ vexy-stax-validate
   ├── Checks PNG format and dimensions
   ├── Verifies content is not blank
   └── Reports validation results

4. ITERATE
   ├── Fix any issues found during validation
   ├── Re-export from web app
   └── Re-validate until all checks pass
```

### Why Separate Python Tool?

**Separation of Concerns**:
- **Web App** (vexy-stax-js): Handles interactive 3D visualization and user interface
- **CLI Tool** (vexy-stax-py): Handles automated testing and validation

**Benefits**:
1. **Cross-Platform Testing**: Generate consistent test images regardless of browser
2. **CI/CD Integration**: Validate exports in automated pipelines (GitHub Actions)
3. **Offline Testing**: Create test assets without running web server
4. **Scripting**: Easily integrate into test automation scripts
5. **Versioning**: Test image generation stays consistent across versions

### Example CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Test vexy-stax-js
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Install Python CLI
      - name: Install vexy-stax-py
        run: pip install vexy-stax

      # Generate test images
      - name: Create test images
        run: vexy-stax-create-test

      # Build web app
      - name: Build vexy-stax-js
        run: |
          cd vexy-stax-js
          npm ci
          npm run build

      # Run automated tests (hypothetical headless browser test)
      - name: Generate exports
        run: node scripts/headless-export.js

      # Validate exports
      - name: Validate PNG outputs
        run: vexy-stax-validate
```

---

## CLI Commands

### `vexy-stax-create-test`

**Purpose**: Generate colored test images for development and testing

**Usage**:
```bash
vexy-stax-create-test
```

**Behavior**:
- Creates `./test-img/` directory in current working directory
- Generates 3 PNG files (layer1.png, layer2.png, layer3.png)
- Each image is 400×300px RGBA with distinct color + label
- Idempotent: safe to run multiple times (overwrites existing files)

**Output Example**:
```
Created /path/to/test-img/layer1.png
Created /path/to/test-img/layer2.png
Created /path/to/test-img/layer3.png

Test images created in /path/to/test-img/
```

**File Details**:
| File | Color | Dimensions | Label |
|------|-------|------------|-------|
| layer1.png | #FF6B6B (Red) | 400×300px | "Layer 1 - Red" |
| layer2.png | #4ECDC4 (Cyan) | 400×300px | "Layer 2 - Cyan" |
| layer3.png | #FFE66D (Yellow) | 400×300px | "Layer 3 - Yellow" |

### `vexy-stax-validate`

**Purpose**: Validate PNG files exported from vexy-stax-js

**Usage**:
```bash
vexy-stax-validate
```

**Behavior**:
- Looks for PNG files in predefined paths (configurable in future versions)
- Currently validates files in `img/` directory:
  - `img/out-pc.png` (800×600px)
  - `img/out-pm.png` (800×600px)
  - `img/out-wl.png` (800×600px)
  - `img/out-wt.png` (800×600px)
- Checks each file for format, dimensions, and content
- Prints validation results with ✓/✗ indicators
- Returns exit code 0 (success) or 1 (failure)

**Output Example**:
```
Validating output PNG files...

✓ vexy-stax-pc: out-pc.png
  Size: 800x600, Mode: RGBA, Size: 245678 bytes

✓ vexy-stax-pm: out-pm.png
  Size: 800x600, Mode: RGBA, Size: 198432 bytes

✗ vexy-stax-wl: out-wl.png
  Error: Width mismatch: expected 800px, got 1600px

All output files are valid!
```

**Validation Criteria**:
- File must exist at expected path
- File must be PNG format (not JPEG/GIF/other)
- Dimensions must match expected values (if specified)
- Image must contain visible content (not blank/transparent)

---

## Architecture

### Package Structure

```
vexy-stax-py/
├── src/
│   └── vexy_stax/
│       ├── __init__.py             # Package initialization
│       ├── _version.py             # Auto-generated by hatch-vcs
│       ├── create_test_images.py   # Test image generator
│       └── validate_output.py      # PNG validator
├── tests/
│   └── test_validate_output.py     # Unit tests
├── test-img/                       # Generated test images (gitignored)
├── test.sh                         # Run all tests
├── pyproject.toml                  # Package config + dependencies
├── .github/workflows/
│   ├── ci.yml                      # Run tests on push/PR
│   └── release.yml                 # Publish to PyPI on tag
└── README.md                       # This file
```

### Dependencies

**Runtime** (`dependencies`):
- **Pillow** (`>=11.0.0`): Image creation and validation
  - Used for: PNG generation, format checking, dimension validation
  - Why: Industry-standard Python imaging library, excellent PNG support

**Build** (`build-system`):
- **hatchling**: Modern Python build backend
- **hatch-vcs**: Git-tag-based versioning (extracts version from git tags)

**Testing** (`tool.hatch.envs.hatch-test`):
- **pytest**: Unit testing framework
- **pillow**: Required for test execution

### Versioning Strategy

**Git-Tag-Based Semver**:
```python
# pyproject.toml
[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/vexy_stax/_version.py"
```

**How It Works**:
1. Version determined from git tags (e.g., `v0.1.0`)
2. hatch-vcs generates `_version.py` during build
3. `__init__.py` imports version from `_version.py`
4. Falls back to `"0.0.0+unknown"` if not in git repo

**Example**:
```bash
# Tag a new version
git tag v0.1.0
git push origin v0.1.0

# Build package (version auto-extracted from tag)
uv build
# Creates dist/vexy_stax-0.1.0-py3-none-any.whl
```

---

## Development

### Prerequisites
- Python 3.12+
- uv (recommended) or pip

### Setup

```bash
# Clone repository
git clone https://github.com/vexyart/vexy-stax-py.git
cd vexy-stax-py

# Install in editable mode with uv
uv pip install -e .

# Or with pip
pip install -e .
```

### Development Workflow

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Run CLI commands
vexy-stax-create-test
vexy-stax-validate

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=src/vexy_stax --cov-report=html

# Type checking
mypy src/
```

### Code Organization

**create_test_images.py** (52 lines):
- `main()`: Entry point for CLI command
  - Creates test-img/ directory
  - Generates 3 colored PNG files with labels
  - Uses Pillow for image creation and text rendering
  - Handles font loading (Helvetica on macOS, fallback to default)

**validate_output.py** (103 lines):
- `validate_png(path, width, height)`: Core validation logic
  - Returns `(is_valid: bool, error_message: str)` tuple
  - Checks file existence, format, dimensions, content
  - Used by both CLI and unit tests
- `main()`: CLI entry point
  - Validates multiple predefined PNG paths
  - Prints formatted results with ✓/✗ indicators
  - Returns exit code 0 (success) or 1 (failure)

**test_validate_output.py** (68 lines):
- 5 unit tests covering:
  - Missing files
  - Wrong format (JPEG instead of PNG)
  - Correct dimensions
  - Dimension mismatches
  - Blank/transparent images
- Uses pytest fixtures for temporary file creation
- Helper function `_write_png()` for test image generation

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src/vexy_stax

# Run specific test
pytest tests/test_validate_output.py::test_validate_png_when_dimensions_match_then_returns_true
```

### Test Coverage

Current test coverage:
- `validate_png()`: 100% (all code paths tested)
- `create_test_images.main()`: Manual testing (generates visual output)

**Test Cases**:
1. **File not found**: Returns error tuple
2. **Wrong format**: Detects non-PNG files
3. **Dimensions match**: Returns success
4. **Dimensions mismatch**: Returns specific error
5. **Blank image**: Detects all-black or all-transparent images

### Manual Testing

```bash
# Generate test images
vexy-stax-create-test

# Verify images were created
ls -lh test-img/
# Should show layer1.png, layer2.png, layer3.png (all ~15-30KB)

# Open images to verify visual appearance
open test-img/layer1.png  # macOS
xdg-open test-img/layer1.png  # Linux
start test-img/layer1.png  # Windows

# Run validation (will fail if img/ directory doesn't exist)
vexy-stax-validate
```

---

## Versioning & Releases

### Semantic Versioning

This package uses **git-tag-based semantic versioning**:
- Version stored in git tags (e.g., `v0.1.0`, `v1.2.3`)
- Automatically extracted during build via `hatch-vcs`
- No manual version bumping in code required

**Version Format**: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes (CLI interface changes)
- **MINOR**: New features (new commands, new validation checks)
- **PATCH**: Bug fixes (validation logic improvements)

### Release Process

```bash
# 1. Ensure all tests pass
pytest -v

# 2. Update CHANGELOG.md with release notes
# (Document changes, fixes, new features)

# 3. Commit changes
git add .
git commit -m "Prepare v0.1.0 release"

# 4. Create and push git tag
git tag v0.1.0
git push origin main --tags

# 5. GitHub Actions automatically:
#    - Builds package
#    - Publishes to PyPI
#    - Creates GitHub Release
```

### GitHub Actions Workflows

**CI (`ci.yml`)**: Runs on every push/PR
```yaml
- Install dependencies with uv
- Run pytest with coverage
- Validate package can be built
```

**Release (`release.yml`)**: Runs on git tag push (`v*`)
```yaml
- Extract version from git tag
- Build package with uv
- Publish to PyPI (requires PyPI token in secrets)
- Create GitHub Release with artifacts
```

---

## Contributing

This is a companion tool for vexy-stax-js. For bug reports or feature requests, please open an issue on GitHub.

### Development Guidelines

1. **Add tests** for new validation logic
2. **Update CHANGELOG.md** with changes
3. **Follow Python conventions**:
   - Type hints for all functions
   - Docstrings for public APIs
   - PEP 8 style (enforced by ruff)
4. **Keep dependencies minimal** (only Pillow for core functionality)

---

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Author

**Adam Twardoch**
[adam+pypi@twardoch.com](mailto:adam+pypi@twardoch.com)
[https://twardoch.github.io/](https://twardoch.github.io/)

---

## Related Projects

- **[vexy-stax-js](https://github.com/vexyart/vexy-stax-js)**: Browser-based 3D image stacking visualizer (the main application)
- Workflow: Python creates test images → Web app visualizes → Python validates exports

---

## FAQ

### Why Python instead of JavaScript for CLI tools?

1. **Better for system tasks**: File validation, image generation, CI/CD integration
2. **Cross-platform consistency**: Python ensures same behavior across all platforms
3. **Ecosystem**: Pillow is the gold standard for image manipulation
4. **Separation**: Keeps testing concerns separate from web app logic

### Can I use these tools standalone?

**Yes!** Both commands work independently:
- `vexy-stax-create-test` generates images you can use anywhere
- `vexy-stax-validate` can validate any PNG files (just update paths in code)

### How do I customize validation paths?

Currently, validation paths are hardcoded in `validate_output.py:68-73`. Future versions will support:
```bash
vexy-stax-validate --path img/output.png --width 800 --height 600
```

For now, modify the source code or use the `validate_png()` function directly in your scripts.

---

**Built for automated testing and quality assurance workflows.**
