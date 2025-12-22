---
this_file: DEPENDENCIES.md
---

# Vexy Stax PY - Dependencies

Comprehensive documentation of all package dependencies and their rationale.

## Core Runtime Dependencies

### Image Processing & Graphics

#### Pillow (>=11.0.0)
**Purpose**: PNG/JPEG image utilities for test image generation
**Why chosen**: Industry-standard Python imaging library
**Used in**: `create_test_images.py` for generating test fixtures
**Alternatives considered**: None - de facto standard
**Status**: ✅ Active use
**Future**: Keep for test utilities; rendering uses pygfx/numpy

#### numpy (>=1.26.0)
**Purpose**: Array operations for image data (RGBA pixels)
**Why chosen**: Universal numerical computing foundation
**Used in**:
- `loader.py` - pixel array storage
- `renderer/*` - texture data, render buffers
**Alternatives considered**: None - required by ecosystem
**Status**: ✅ Core dependency
**Future**: Essential for rendering pipeline

#### imageio (>=2.36.0) + imageio-ffmpeg
**Purpose**: Image I/O with PNG/video encoding support
**Why chosen**: Simple API, FFmpeg integration for video (H.264/ProRes)
**Used in**: `renderer/export.py` for PNG/video writing
**Extras**: `imageio[ffmpeg]` installs `imageio-ffmpeg` for H.264 codec
**Alternatives considered**:
- PIL/Pillow (lacks video)
- opencv-python (heavy dependency)
- PyAV (more complex API)
**Status**: ✅ Active use
**Future**: Keep for export functionality

### Rendering Engine

#### pygfx (>=0.15.0)
**Purpose**: GPU-accelerated 3D rendering engine
**Why chosen**: Pure Python, modern graphics, headless rendering
**Used in**: `renderer/*` modules for scene graph, materials, camera
**Alternatives considered**:
- Three.js via Playwright (current workaround, heavyweight)
- Blender Python API (overkill for our needs)
- PyOpenGL (lower-level, more complex)
**Status**: ⚠️ Implemented but not wired to CLI (Issue 102)
**Future**: Will become primary rendering path in v2.0

#### wgpu (>=0.17.0)
**Purpose**: WebGPU backend for pygfx (GPU access)
**Why chosen**: Required by pygfx, cross-platform GPU API
**Used in**: `renderer/context.py` for GPU device probing
**Alternatives considered**: None - pygfx dependency
**Status**: ⚠️ Scaffolding exists, no GPU smoke test (Issue 103)
**Future**: Core dependency for headless rendering
**Notes**: Requires GPU drivers (Metal/Vulkan/DX12) or software rendering

### Browser Automation (Legacy Path)

#### Playwright (>=1.40.0)
**Purpose**: Browser automation for vexy-stax-js control
**Why chosen**: Reliable cross-browser automation, good async API
**Used in**: `browser.py`, `cli.py` (current primary path)
**Alternatives considered**:
- Selenium (older, less stable)
- Puppeteer (Node.js only)
**Status**: ✅ Working but deprecated (Issue 107)
**Future**: Move to optional dependency group `[playwright]` in v2.0
**Rationale**: Pygfx rendering eliminates need for browser

### Data Validation

#### Pydantic (>=2.8.0)
**Purpose**: Scene JSON schema validation with type safety
**Why chosen**: Excellent validation errors, auto-generated docs
**Used in**: `models.py` for SceneConfig/SceneImage/SceneParams
**Alternatives considered**:
- dataclasses + manual validation (verbose, error-prone)
- marshmallow (less modern API)
**Status**: ✅ Core validation layer
**Future**: Keep for robust input handling

### CLI Interface

#### Fire (>=0.6.0)
**Purpose**: CLI command generation from class methods
**Why chosen**: Zero-boilerplate CLI from Python functions
**Used in**: `cli.py` main entry point
**Alternatives considered**:
- Click (more verbose, manual arg definitions)
- Typer (considered for v2.0, Rich integration)
- argparse (stdlib, too low-level)
**Status**: ✅ Working transitional choice
**Future**: May migrate to Typer for better Rich/progress integration
**Notes**: Fire chosen for rapid prototyping; Typer deferred until CLI stabilizes

## Development Dependencies

### Testing

#### pytest (hatch-test env)
**Purpose**: Test framework and runner
**Why chosen**: Industry standard, excellent fixtures/parametrization
**Used in**: All `tests/test_*.py` files
**Status**: ✅ 59 tests passing

### Code Quality (Not in pyproject.toml - invoked via uvx)

#### autoflake
**Purpose**: Remove unused imports
**Invoked**: `uvx autoflake -i {}`
**Status**: Part of /test hygiene chain

#### pyupgrade
**Purpose**: Upgrade syntax to Python 3.12+
**Invoked**: `uvx pyupgrade --py312-plus {}`
**Status**: Part of /test hygiene chain

#### ruff
**Purpose**: Fast linting and formatting
**Invoked**: `uvx ruff check/format`
**Status**: Part of /test hygiene chain

## Dependency Audit Findings

### Redundancy
- Both `playwright` and `pygfx` installed but only Playwright used in CLI
- **Action**: After v2.0, move Playwright to optional `[playwright]` group

### Missing Documentation
- No `loguru` currently used despite PLAN.md mention
- **Action**: Add when implementing `--verbose` mode (Issue 108)

### Version Pinning Strategy
- Using `>=` with major.minor for all deps
- **Rationale**: Allow patch updates, prevent breaking changes
- **Risk**: Dependency breakage possible; add upper bounds if issues arise

## Transitive Dependencies (Auto-installed)

### Via pygfx
- `rendercanvas` - Headless canvas wrapper
- `pylinalg` - Linear algebra helpers
- `freetype-py` - Font rendering (if text needed)
- `uharfbuzz` - Text shaping (if text needed)

### Via wgpu
- `wgpu-native` binaries - Rust WebGPU implementation

### Via Playwright
- Chromium binaries (~400 MB) - Browser rendering engine

## Total Package Size Estimate

**Current install** (~500 MB):
- Python packages: ~50 MB
- Playwright browsers: ~400 MB
- wgpu/pygfx assets: ~50 MB

**Future v2.0** (~100 MB):
- Python packages: ~50 MB
- wgpu/pygfx assets: ~50 MB
- Playwright: optional, not installed by default

**Savings**: ~80% size reduction by deprecating Playwright

## Platform-Specific Requirements

### macOS
- ✅ Metal drivers (built-in)
- ✅ pygfx works out of box

### Linux
- Requires: Vulkan drivers (`vulkan-tools`, `mesa-vulkan-drivers`)
- Optional: X11/Wayland for Playwright (if used)

### Windows
- Requires: DirectX 12 drivers (usually present)
- wgpu-native includes DX12 support

### Headless/Docker
- **Issue 104**: GPU access required or software rendering needed
- Options: GPU passthrough, Mesa llvmpipe, or Playwright fallback

## Security Considerations

### Direct Vulnerabilities
- No known CVEs in current versions (as of 2025-11-06)
- Action: Add `pip-audit` to CI for continuous monitoring

### Indirect Risks
- Playwright downloads binaries - verify signatures
- wgpu-native Rust binaries - trust pygfx maintainers

## Future Dependency Changes

### Planned Additions
- `rich` - Progress bars, beautiful console output (Issue 108)
- `scikit-image` - Image comparison metrics (Issue 105)
  - For SSIM, MAE, PSNR quality validation

### Planned Removals
- `playwright` → optional `[playwright]` group

### Under Consideration
- `typer` - Replace Fire for better CLI with Rich integration
- `loguru` - Structured logging for `--verbose` mode
- `av` (PyAV) - Video encoding (imageio dependency, may need explicit add)

## Dependency Decision Matrix

When adding a new dependency, evaluate:

1. **Necessity**: Can we achieve goal without it?
   - Try stdlib first
   - Check if existing deps provide functionality

2. **Maturity**: Is it production-ready?
   - \>200 GitHub stars
   - Recent updates (< 6 months)
   - Good documentation

3. **Maintenance**: Is it actively maintained?
   - Check issue response time
   - Release cadence
   - Python version support

4. **Size**: What's the installation cost?
   - Small utilities: <1 MB acceptable
   - Large tools: justify carefully
   - Transitive deps: investigate

5. **Alternatives**: What else was considered?
   - Document why chosen over alternatives
   - Note trade-offs

## Package Installation Commands

```bash
# Production install (future v2.0)
pip install vexy-stax

# With optional Playwright support
pip install vexy-stax[playwright]

# Development install
git clone https://github.com/vexyart/vexy-stax-py
cd vexy-stax-py
uv sync
```

## Dependency Graph Summary

```
vexy-stax
├── Core Rendering
│   ├── pygfx (3D engine)
│   │   └── wgpu (GPU access)
│   │       └── wgpu-native (Rust binaries)
│   └── numpy (arrays)
│
├── I/O & Validation
│   ├── imageio (PNG/video)
│   ├── pillow (test images)
│   └── pydantic (validation)
│
├── CLI & Automation
│   ├── fire (CLI generator)
│   └── playwright (browser automation - deprecated)
│       └── chromium (400 MB binary)
│
└── Development (not in wheel)
    └── pytest (testing)
```

## Related Documentation

- `pyproject.toml` - Canonical dependency list
- `PLAN.md` - Dependency evolution roadmap
- `issues/104-gpu-strategy-missing.md` - GPU dependency challenges
- `issues/102-architectural-disconnect.md` - Playwright vs pygfx choice

---

**Last Updated**: 2025-11-06
**Dependencies Count**: 8 runtime + 1 dev (+ transitive)
**Total Install Size**: ~500 MB (current), ~100 MB (future)
