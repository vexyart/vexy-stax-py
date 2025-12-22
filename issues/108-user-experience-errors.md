---
this_file: issues/108-user-experience-errors.md
priority: MEDIUM
category: User Experience
created: 2025-11-06
---

# Issue 108: Poor Error Messages, Missing Validation, UX Gaps

## Problem Statement

When things go wrong—and they will—users face cryptic errors, missing validation, and no guidance. Good UX means anticipating failures and providing helpful, actionable error messages.

## Error Message Audit

### Example 1: Missing Dev Server (Current)
```bash
$ vexy-stax render --images scene.json --output out.png

RuntimeError: Cannot connect to http://localhost:5173/vexy-stax-js/
Make sure the dev server is running:
  cd vexy-stax-js && npm run dev
```

**Issues**:
- Assumes user has vexy-stax-js repo cloned
- Doesn't explain where to get it
- No alternative offered

**Better**:
```bash
$ vexy-stax render --images scene.json --output out.png

❌ Cannot connect to vexy-stax-js dev server at http://localhost:5173

Prerequisites (v1.x browser automation):
  1. Clone vexy-stax-js:
     → git clone https://github.com/vexyart/vexy-stax-js
  2. Install dependencies:
     → cd vexy-stax-js && npm install
  3. Start server (keep running):
     → npm run dev

Alternative: Wait for v2.0 with native rendering (no server needed)
Help: https://github.com/vexyart/vexy-stax-py#troubleshooting

Error code: ECONNREFUSED [5001]
```

### Example 2: Invalid Scale (Current)
```python
# In cli.py:131-133
try:
    validate_scale(scale)
except ValueError as exc:
    print(f"Error: {exc}")
    return
```

**Issue**: Just prints exception message, no guidance

**Better**:
```bash
$ vexy-stax render --images scene.json --output out.png --scale 5

❌ Invalid scale: 5

Supported scales: 1, 2, 4
  • 1x: Base resolution (800x600 → 800x600)
  • 2x: High quality (800x600 → 1600x1200)
  • 4x: Maximum quality (800x600 → 3200x2400, ~16 MB PNG)

Example: vexy-stax render --images scene.json --scale 2

Error code: INVALID_SCALE [1002]
```

### Example 3: Scene File Not Found (Current Behavior Unknown)
```bash
$ vexy-stax render --images missing.json --output out.png

# Current: Probably crashes with file not found
```

**Better**:
```bash
❌ Scene file not found: missing.json

Check:
  • File path is correct (use absolute or relative to current directory)
  • File exists: ls -la missing.json
  • File has .json extension
  • File is readable: cat missing.json

Current directory: /Users/adam/projects/renders
Searched for: /Users/adam/projects/renders/missing.json

Error code: FILE_NOT_FOUND [2001]
```

### Example 4: Invalid JSON (Current Behavior Unknown)
```bash
$ vexy-stax render --images corrupt.json --output out.png

# Current: Probably shows JSON parse error
```

**Better**:
```bash
❌ Cannot parse scene file: corrupt.json

JSON syntax error at line 15, column 8:
  "images": [
    {"filename": "layer1.png"  ← Missing closing brace
  ]

Fix:
  • Validate JSON: cat corrupt.json | python -m json.tool
  • Re-export from vexy-stax-js
  • Check for truncation/corruption

Error code: INVALID_JSON [2002]
```

### Example 5: Scene Schema Validation (Current - Loader Validates)
`loader.py` uses Pydantic but validation errors probably cryptic:

```bash
$ vexy-stax render --images bad-schema.json --output out.png

# Current: Pydantic validation error dump
```

**Better**:
```bash
❌ Scene file has invalid schema: bad-schema.json

Validation errors:
  1. params.z_spacing: Must be >= 0.0 (got: -0.5)
  2. images[0].width: Required field missing
  3. camera_mode: Invalid value 'tilt'. Allowed: perspective, telephoto, orthographic

Fix:
  • Re-export scene from vexy-stax-js (latest version)
  • Check scene format version (found: "0.9", expected: "1.0")
  • Manually edit JSON to fix errors

Docs: https://github.com/vexyart/vexy-stax-py/blob/main/docs/SCENE-FORMAT.md

Error code: SCHEMA_VALIDATION [2003]
```

## Missing Validation

### Input Path Validation
**Current**: Accepts any string, errors later
**Needed**: Upfront validation

```python
def validate_input_path(images: str) -> Path:
    """Validate and normalize input path."""

    path = Path(images)

    if not path.exists():
        raise InputError(
            f"Path not found: {images}\n"
            f"  Absolute path: {path.absolute()}\n"
            f"  Current directory: {Path.cwd()}\n"
            f"\nCheck file path is correct."
        )

    if path.is_file():
        if path.suffix.lower() not in ['.json']:
            raise InputError(
                f"Input file must be JSON: {images}\n"
                f"  Found: {path.suffix}\n"
                f"  Expected: .json (scene file)\n"
                f"\nExport scene from vexy-stax-js as JSON."
            )
        return path

    if path.is_dir():
        images = list(path.glob("*.png"))
        if not images:
            raise InputError(
                f"No PNG files in directory: {images}\n"
                f"  Directory: {path.absolute()}\n"
                f"  Files found: {len(list(path.iterdir()))}\n"
                f"\nAdd PNG files or use JSON scene file instead."
            )
        return path

    raise InputError(f"Path must be JSON file or directory with PNGs: {images}")
```

### Output Path Validation
```python
def validate_output_path(output: str, overwrite: bool = False) -> Path:
    """Validate output path."""

    path = Path(output)

    # Check parent directory exists
    if not path.parent.exists():
        raise OutputError(
            f"Output directory doesn't exist: {path.parent}\n"
            f"\nCreate directory first:\n"
            f"  mkdir -p {path.parent}"
        )

    # Check not overwriting
    if path.exists() and not overwrite:
        raise OutputError(
            f"Output file already exists: {output}\n"
            f"\nChoices:\n"
            f"  • Use different filename\n"
            f"  • Add --overwrite flag\n"
            f"  • Delete existing: rm {output}"
        )

    # Check writable
    if path.exists() and not os.access(path, os.W_OK):
        raise OutputError(
            f"Output file not writable: {output}\n"
            f"  Permissions: {oct(path.stat().st_mode)}\n"
            f"\nFix permissions:\n"
            f"  chmod u+w {output}"
        )

    # Check parent writable
    if not os.access(path.parent, os.W_OK):
        raise OutputError(
            f"Cannot write to directory: {path.parent}\n"
            f"  Permissions: {oct(path.parent.stat().st_mode)}\n"
            f"\nFix permissions:\n"
            f"  chmod u+w {path.parent}"
        )

    return path
```

### Animation Timing Validation
```python
def validate_animation_params(duration: float, hold: float, fps: int):
    """Validate animation parameters."""

    if duration <= 0:
        raise AnimationError(
            f"Duration must be positive: {duration}s\n"
            f"  Typical range: 1.0 - 5.0 seconds\n"
            f"  Recommended: 2.0s for smooth animation"
        )

    if hold < 0:
        raise AnimationError(
            f"Hold time cannot be negative: {hold}s\n"
            f"  Use 0 for no hold, or positive value\n"
            f"  Recommended: 0.5s to showcase final position"
        )

    if fps not in [24, 25, 30, 60]:
        print(
            f"⚠️  Warning: Unusual frame rate: {fps} fps\n"
            f"   Standard rates: 24, 25, 30, 60\n"
            f"   Your video may not play smoothly."
        )

    if fps * duration > 1000:
        print(
            f"⚠️  Warning: High frame count: {int(fps * duration)} frames\n"
            f"   Render time: ~{int(fps * duration * 0.5)}s (estimated)\n"
            f"   File size: ~{int(fps * duration * 0.1)} MB (estimated)\n"
            f"   Consider reducing duration or fps."
        )
```

## UX Improvements

### 1. Dry-Run Mode
```bash
$ vexy-stax render --images scene.json --output out.png --dry-run

✓ Validation checks passed:
  • Scene file: test-img/layer123.json (valid)
  • Images: 3 layers (total 2.1 MB)
  • Output: out.png (will be created)
  • Scale: 2x (1600x1200)
  • Estimated render time: 1.2s
  • Estimated file size: 4.5 MB

Ready to render. Remove --dry-run to proceed.
```

### 2. Interactive Mode
```bash
$ vexy-stax render --interactive

Vexy Stax Interactive Render
=============================

Scene file: [Browse...] or enter path: test-img/layer123.json
Output path: render.png
Scale: [1x] 2x [4x]
Format: [PNG] JPG WebP

[Preview Scene] [Render] [Cancel]
```

### 3. Verbose Mode
```bash
$ vexy-stax render --images scene.json --output out.png --verbose

[INFO] Validating input path: scene.json
[INFO] Loading scene: test-img/layer123.json
[DEBUG] Scene version: 1.0
[DEBUG] Images: 3 layers
[DEBUG]   layer1.png: 800x600 (RGBA, 1.2 MB)
[DEBUG]   layer2.png: 800x600 (RGBA, 1.1 MB)
[DEBUG]   layer3.png: 800x600 (RGB, 0.9 MB)
[INFO] Creating renderer (backend: playwright)
[DEBUG] Launching Chromium...
[DEBUG] Connecting to http://localhost:5173
[INFO] Loading images to browser...
[DEBUG] Uploaded 3 images in 0.3s
[INFO] Rendering at 2x scale (1600x1200)...
[DEBUG] Export PNG command sent
[DEBUG] Waiting for download...
[INFO] Saved: out.png (4.5 MB)
[INFO] Render complete in 1.2s
```

### 4. Progress Indicators
```python
from rich.console import Console
from rich.progress import track

console = Console()

# For multiple operations
with console.status("[bold green]Rendering scene...") as status:
    status.update("[cyan]Loading scene...")
    scene = load_scene(path)

    status.update("[cyan]Creating renderer...")
    renderer = create_renderer()

    status.update("[cyan]Rendering frame...")
    frame = renderer.render(scene)

    status.update("[cyan]Encoding PNG...")
    save_png(frame, output)

console.print("[green]✓[/green] Render complete!")
```

### 5. Configuration File Support
```bash
# .vexy-stax.toml or vexy-stax.toml
[defaults]
scale = 2
backend = "pygfx"
overwrite = false

[animation]
fps = 30
duration = 2.0
hold = 0.5

[output]
directory = "renders/"
name_template = "{scene}_{scale}x_{timestamp}.png"

[gpu]
prefer = "high-performance"
allow_software = true
```

```bash
# Uses config defaults
$ vexy-stax render --images scene.json

# Override specific settings
$ vexy-stax render --images scene.json --scale 4 --output custom.png
```

## Error Code System

Implement consistent error codes for documentation/troubleshooting:

| Code | Category | Example |
|------|----------|---------|
| 1xxx | CLI Arguments | 1001: Missing required argument |
| 2xxx | File Operations | 2001: File not found, 2002: Invalid JSON |
| 3xxx | Rendering | 3001: GPU unavailable, 3002: Shader error |
| 4xxx | Network | 4001: Cannot connect to server |
| 5xxx | Encoding | 5001: Codec unavailable, 5002: Video write failed |

Each error links to docs:
```
Error code: 3001
https://github.com/vexyart/vexy-stax-py/blob/main/docs/errors/3001.md
```

## Success Criteria

1. ✅ Every failure has helpful error message
2. ✅ Error messages include next steps
3. ✅ Common errors documented in TROUBLESHOOTING.md
4. ✅ Validation happens upfront (fail fast)
5. ✅ --dry-run mode validates without executing
6. ✅ --verbose mode shows detailed progress
7. ✅ Error codes documented with examples

## Implementation Priority

### Phase 1: Critical Errors (Week 1)
- Server connection errors
- File not found errors
- Invalid scale errors
- Scene validation errors

### Phase 2: Validation (Week 1-2)
- Input path validation
- Output path validation
- Animation parameter validation
- Schema validation improvements

### Phase 3: UX Polish (Week 2)
- Progress indicators
- Dry-run mode
- Verbose logging
- Configuration file support

### Phase 4: Documentation (Week 2-3)
- TROUBLESHOOTING.md with all common errors
- Error code reference
- FAQ section

## Related Issues

- Issue 107: Documentation (error messages link to docs)
- Issue 104: GPU strategy (GPU errors need good messages)
- Issue 102: Architectural disconnect (server errors critical)

## Priority Justification

**MEDIUM** because:
- Improves user experience significantly
- Reduces support burden
- But: System works for users who figure it out
- Can be done incrementally
- Lower priority than core functionality working
