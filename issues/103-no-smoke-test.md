---
this_file: issues/103-no-smoke-test.md
priority: CRITICAL
category: Testing
created: 2025-11-06
---

# Issue 103: No Smoke Test Validates Actual Rendering

## Problem Statement

Test suite passes (53/53) but **not a single test actually renders anything with pygfx**. All rendering is mocked with stubs returning fake RGBA arrays. This creates false confidence and means the core functionality—rendering scenes—is completely untested.

## Current Test Reality

### Example from `tests/test_renderer_pipeline.py:32-41`
```python
class StubRenderer:
    def __init__(self) -> None:
        self.rendered: list[tuple[object, object]] = []

    def render(self, scene: object, camera: object) -> np.ndarray:
        self.rendered.append((scene, camera))
        image = np.zeros((16, 16, 4), dtype=np.uint8)
        image[..., :3] = 127
        image[..., 3] = 255
        return image  # ← Returns gray box, never touches GPU
```

### What Tests Actually Validate
✓ Dependency injection wiring works
✓ Data flows through interfaces correctly
✓ Type signatures are correct
✓ Error handling logic executes

### What Tests Don't Validate
✗ GPU is accessible
✗ pygfx can create canvas
✗ Textures upload to GPU
✗ Shaders compile
✗ Rendering produces valid pixels
✗ PNG export creates readable files
✗ Video encoding works
✗ Materials look correct
✗ Camera framing is accurate

## Smoke Test Definition

A smoke test should:
1. Load a real JSON scene fixture
2. Create actual pygfx canvas and renderer
3. Build real geometry, materials, textures
4. Render one frame with real GPU
5. Export to PNG file on disk
6. Validate PNG is readable and has expected properties

**Currently**: None of this happens
**Impact**: Could ship completely broken renderer with green tests

## Concrete Example of Missing Coverage

### Test Claims to Work (`tests/test_renderer_pipeline.py:61-114`)
```python
def test_renderer_pipeline_generates_png_and_video(tmp_path: Path) -> None:
    # ...creates stubs...
    result = export_png(
        bundle=canvas_bundle,
        scene=assembled_scene,
        camera=camera,
        output_path=png_path,
        width=scene.images[0].width,
        height=scene.images[0].height,
        scale=1,
        render_fn=canvas_bundle.renderer.render,  # ← Stub!
        writer=lambda path, image: np.save(...)   # ← Writes .npy not PNG!
    )
    assert result.path == png_path  # ← File doesn't exist!
```

Test passes but:
- No actual PNG file created
- No real rendering happened
- No GPU touched
- Writer saves numpy array to `.npy` file
- Assertion checks path object, not file existence

## Why This Happened

1. **Good Design, Wrong Testing**: Dependency injection enables clean testing but allowed complete stubbing
2. **GPU Test Avoidance**: Developers avoided GPU-dependent tests due to CI concerns
3. **Incremental Development**: Planned to add real tests "later"
4. **Test Coverage Metrics Mislead**: 100% code coverage with 0% actual validation

## Proposed Smoke Test

```python
# tests/test_smoke_real_render.py
import pytest
from pathlib import Path
from PIL import Image

def test_pygfx_smoke_render_actual_png(tmp_path: Path) -> None:
    """Smoke test: Load scene, render with real pygfx, export PNG."""

    # Skip if GPU unavailable (but log warning)
    try:
        from vexy_stax.renderer import probe_gpu, create_offscreen_dependencies
        probe_gpu(device_getter=..., power_preference="high-performance")
    except GPUUnavailableError:
        pytest.skip("GPU unavailable - smoke test requires hardware rendering")

    # Load real test scene
    from vexy_stax.loader import load_scene
    scene_path = Path("test-img/layer123.json")
    scene = load_scene(scene_path)

    # Create REAL renderer (no mocks)
    from vexy_stax.render_pipeline import pygfx_render
    output = tmp_path / "smoke.png"

    # This must use actual pygfx, not stubs
    result = pygfx_render(
        scene=scene,
        output_path=output,
        width=800,
        height=600,
        scale=1
    )

    # Validate real PNG file
    assert output.exists(), "PNG file must be created"
    assert output.stat().st_size > 1000, "PNG must have real content"

    # Validate image properties
    img = Image.open(output)
    assert img.format == "PNG"
    assert img.size == (800, 600)
    assert img.mode == "RGBA"

    # Validate rendering actually happened (not blank)
    pixels = list(img.getdata())
    unique_colors = len(set(pixels[:100]))  # Sample first 100 pixels
    assert unique_colors > 2, "Image must have content, not be blank"

    print(f"✓ Smoke test passed: {output} ({output.stat().st_size} bytes)")
```

## Implementation Requirements

### Step 1: Make Test Runnable
Create `src/vexy_stax/render_pipeline.py` with:
```python
def pygfx_render(scene: SceneConfig, output_path: Path,
                 width: int, height: int, scale: int) -> PNGExportResult:
    """End-to-end render using real pygfx."""
    # 1. Create offscreen renderer context
    # 2. Prepare textures from scene.images
    # 3. Build scene graph
    # 4. Create camera
    # 5. Render frame
    # 6. Export to PNG
    # 7. Return result
```

### Step 2: Handle GPU Unavailability
- Detect GPU in test setup
- Skip test on CI/headless environments with clear message
- Log warning when skipped so we know coverage gap
- Document how to enable in CI (e.g., software rendering)

### Step 3: Add to CI Workflow
```yaml
# .github/workflows/ci.yml
- name: Install GPU dependencies (optional)
  run: |
    # Try to install Mesa/swiftshader for software rendering
    # If fails, smoke test will skip
    sudo apt-get install -y mesa-vulkan-drivers || true

- name: Run tests (including smoke)
  run: uv run pytest -v
  env:
    WGPU_BACKEND: vulkan  # Force software rendering
```

## Success Criteria

1. ✅ New test `tests/test_smoke_real_render.py` exists
2. ✅ Test creates actual PNG file on disk
3. ✅ Test validates PNG properties (size, format, content)
4. ✅ Test uses real pygfx/wgpu (no mocks)
5. ✅ Test skips gracefully when GPU unavailable
6. ✅ CI workflow attempts to run test (may skip on some runners)

## Risk Mitigation

### Risk: Test flaky on CI
**Mitigation**: Mark as `@pytest.mark.gpu_required`, allow skip, but fail if implementation broken

### Risk: Test slow
**Mitigation**: Single small scene (100x100), minimal rendering, <2s timeout

### Risk: Can't run locally for some developers
**Mitigation**: Clear skip message explains GPU requirement, link to docs

## Related Issues

- Issue 102: Architectural disconnect (smoke test proves integration works)
- Issue 104: GPU detection strategy (smoke test exercises detection)
- Issue 105: Quality validation (smoke test is first quality check)

## Current State Evidence

```bash
$ grep -r "pygfx" tests/
# Results: Lots of imports, zero actual usage
tests/test_renderer_context.py:    from pygfx import ...  # In skip conditions only
tests/test_renderer_*.py: # All use stubs

$ grep -r "StubRenderer\|StubCanvas" tests/
tests/test_renderer_pipeline.py:32:class StubRenderer:
tests/test_renderer_pipeline.py:24:class StubCanvas:
# All tests use stubs, none use real pygfx
```

## Priority Justification

**CRITICAL** because:
1. Entire renderer could be broken with passing tests
2. Blocks quality validation work
3. False sense of test coverage
4. Could ship to users without working
5. Prerequisite for all other renderer validation work
