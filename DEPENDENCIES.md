<!-- this_file: DEPENDENCIES.md -->

# Dependencies

## Runtime

| Package | Version | Purpose |
|---------|---------|---------|
| `fire` | latest | CLI argument parsing and automatic help generation |
| `rich` | latest | Colored console output and formatting |
| `pillow` | latest | Image I/O, overlay compositing (pure-Pillow flat render) |
| `numpy` | latest | Pixel math, array operations for geometry |
| `pydantic` | ≥2 | Strict scene model validation at I/O boundary; `extra="forbid"` on all models |
| `opencv-python-headless` | latest | Per-channel color matching and correction (juicy.py) |
| `pygfx` | ≥0.16.0 | GPU/wgpu offscreen render engine (still-image backend) |
| `pylinalg` | ≥0.6.8 | Linear algebra for 3D transformations in geometry math |
| `playwright` | ≥1.60.0 | Drives the JS build headless in Chromium for playwright engine |

## System

| Tool | Installation | Purpose |
|------|--------------|---------|
| Blender | `brew install --cask blender` | Subprocess renderer for high-fidelity offline renders; not a pip package |
| ffmpeg | `brew install ffmpeg` | Video assembly from PNG frame sequences into MP4/WebM |

## Development

See `pyproject.toml` `[tool.hatch.envs.default]`: pytest, pytest-cov.
