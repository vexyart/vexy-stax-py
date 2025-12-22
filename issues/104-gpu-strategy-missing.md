---
this_file: issues/104-gpu-strategy-missing.md
priority: HIGH
category: Infrastructure
created: 2025-11-06
---

# Issue 104: No GPU Detection, Fallback Strategy, or User Guidance

## Problem Statement

Renderer depends on GPU via wgpu but provides no strategy for environments without GPU access. Users get cryptic errors, no guidance, and no fallback. Critical for CI/CD, Docker containers, headless servers, and older hardware.

## User Impact Scenarios

### Scenario 1: CI/CD Pipeline
```yaml
# .github/workflows/render.yml
- name: Render scenes
  run: |
    vexy-stax render --images scene.json --output render.png
```

**Current behavior**:
```
RuntimeError: No suitable GPU adapter available
```

**No guidance on**:
- Whether to install drivers
- Which drivers
- If software rendering possible
- Fallback to browser rendering
- How to skip gracefully

### Scenario 2: Docker Container
```dockerfile
FROM python:3.12-slim
RUN pip install vexy-stax
# No GPU drivers, no display
```

**User runs**: `docker run myimage vexy-stax render --images scene.json`
**Result**: Cryptic wgpu initialization error

**Expected**: Clear message about GPU requirement, link to docs

### Scenario 3: Developer Without Discrete GPU
MacBook Air with integrated graphics, or Linux VM without GPU passthrough

**Current**: Unknown if it works
**Needed**: Detection shows "Using integrated GPU (slower)" or "Software rendering"

### Scenario 4: Remote Server
SSH into headless Linux server, no X11 forwarding

**Current**: Unknown behavior
**Needed**: Headless rendering with software fallback

## Current Code Analysis

### Context Creation (`src/vexy_stax/renderer/context.py:86-90`)
```python
def _default_device_getter(**kwargs: Any) -> Any:
    import wgpu.backends.rs  # noqa: F401 - register backend
    from wgpu.utils import get_default_device

    return get_default_device(**kwargs)
```

**Issues**:
1. No error message customization
2. No adapter enumeration
3. No preference checking (high-performance vs low-power)
4. No software rendering fallback
5. No logging of available adapters

### Error Handling (`src/vexy_stax/renderer/context.py:20-31`)
```python
def probe_gpu(
    *,
    device_getter: DeviceGetter,
    power_preference: str = "high-performance",
    **kwargs: Any,
) -> Any:
    """Return a GPU device or raise ``GPUUnavailableError`` when not accessible."""

    try:
        return device_getter(power_preference=power_preference, **kwargs)
    except RuntimeError as exc:  # pragma: no cover
        raise GPUUnavailableError("No suitable GPU adapter available") from exc
```

**Issues**:
1. Generic error message
2. No diagnostic information
3. No suggestions for user
4. No distinction between "no GPU" vs "drivers missing" vs "permissions"

## Required Capabilities

### 1. Detection and Diagnostics
```python
from vexy_stax.gpu_doctor import diagnose_gpu

def diagnose_gpu() -> GPUDiagnosis:
    """Probe GPU availability and capabilities."""
    return GPUDiagnosis(
        available=True/False,
        adapter_type="discrete" | "integrated" | "software" | "none",
        adapter_name="NVIDIA RTX 3080" | "Apple M2" | ...,
        backend="vulkan" | "metal" | "dx12" | "webgpu",
        software_rendering_available=True/False,
        estimated_performance="high" | "medium" | "low",
        warnings=["Old drivers detected", ...],
        recommendations=["Upgrade to driver X.Y", ...]
    )
```

### 2. User-Facing Doctor Command
```bash
$ vexy-stax doctor

Vexy Stax GPU Diagnosis
=======================

GPU Detection: ✓ Found
  Adapter: NVIDIA RTX 3080
  Backend: Vulkan 1.3
  Type: Discrete GPU
  Performance: High

Rendering: ✓ Ready
  Offscreen: Supported
  Max Texture Size: 16384x16384
  Memory Available: 8 GB

Recommendations:
  • System ready for rendering
  • Expected render time: 0.5s per frame @ 1920x1080

$ vexy-stax doctor  # On machine without GPU

GPU Detection: ✗ No GPU Found
  Available: None
  Checked: Vulkan, Metal, DX12

Software Rendering: ✓ Available
  Backend: SwiftShader (CPU emulation)
  Performance: Low (10-20x slower)

Recommendations:
  • Install GPU drivers: [link to guide]
  • Or: Use software rendering with --force-cpu
  • Or: Fall back to Playwright mode with --backend=playwright

Docker users: See docs.example.com/docker-gpu
CI/CD: See docs.example.com/ci-rendering
```

### 3. Automatic Fallback Chain
```python
def create_renderer(
    *,
    prefer_gpu: bool = True,
    allow_software: bool = True,
    allow_playwright: bool = False,
) -> RendererContext:
    """Create renderer with fallback chain."""

    attempts = []

    if prefer_gpu:
        try:
            return _create_gpu_renderer("high-performance")
        except GPUUnavailableError as e:
            attempts.append(("GPU (high-perf)", str(e)))

        try:
            return _create_gpu_renderer("low-power")
        except GPUUnavailableError as e:
            attempts.append(("GPU (low-power)", str(e)))

    if allow_software:
        try:
            return _create_software_renderer()
        except SoftwareRenderingUnavailable as e:
            attempts.append(("Software rendering", str(e)))

    if allow_playwright:
        return _create_playwright_renderer()

    # All failed
    raise RendererUnavailableError(
        "No rendering backend available\n" +
        "Attempted:\n" +
        "\n".join(f"  - {name}: {err}" for name, err in attempts) +
        "\n\nRun 'vexy-stax doctor' for diagnosis"
    )
```

### 4. CLI Flags for Control
```bash
# Explicit backend selection
vexy-stax render --backend=gpu --images scene.json
vexy-stax render --backend=software --images scene.json
vexy-stax render --backend=playwright --images scene.json

# Auto with preferences
vexy-stax render --prefer-gpu --allow-software --images scene.json

# Force specific behavior
vexy-stax render --force-cpu --images scene.json  # Software only
vexy-stax render --require-gpu --images scene.json  # Fail if no GPU

# CI-friendly flags
vexy-stax render --no-gpu-warning --images scene.json  # Suppress perf warnings
```

## Software Rendering Investigation

### WGPU Software Rendering
wgpu-py may support software rendering via:
- **SwiftShader**: Vulkan emulation on CPU
- **Mesa llvmpipe**: Software OpenGL/Vulkan
- **WebGPU fallback**: Browser-based software rendering

**Action Required**: Research and document which work with pygfx

### Playwright as Fallback
Since Playwright is currently installed:
- Keep as emergency fallback
- Auto-enable if GPU unavailable and user approves
- Eventually make optional dependency

## Implementation Plan

### Phase 1: Detection (Week 1)
1. Implement `gpu_doctor.py` with adapter enumeration
2. Add `diagnose_gpu()` function
3. Create `vexy-stax doctor` CLI command
4. Test on: macOS (Metal), Linux (Vulkan), WSL (software)

### Phase 2: Better Errors (Week 1)
1. Enhance `GPUUnavailableError` with diagnosis
2. Add recommendations to error messages
3. Link to documentation
4. Test error messages on systems without GPU

### Phase 3: Software Fallback (Week 2)
1. Research wgpu software rendering
2. Implement CPU-based rendering
3. Add performance warnings
4. Benchmark and document speed penalty

### Phase 4: CLI Integration (Week 2)
1. Add `--backend` flag
2. Implement fallback chain
3. Add `--require-gpu` / `--allow-software` flags
4. Update help text and docs

## Documentation Requirements

### New Docs Needed
1. **Installation guide per platform**:
   - macOS: Built-in Metal support
   - Linux: Vulkan driver installation
   - Windows: DirectX requirements
   - Docker: GPU passthrough setup

2. **Troubleshooting guide**:
   - "No GPU adapter found" → solutions
   - Driver version requirements
   - Software rendering setup
   - Performance expectations

3. **CI/CD recipes**:
   - GitHub Actions with/without GPU
   - GitLab CI GPU runners
   - Docker with GPU access
   - Software rendering in containers

## Success Criteria

1. ✅ `vexy-stax doctor` command provides clear GPU status
2. ✅ Clear error messages with actionable recommendations
3. ✅ Software rendering works on machines without GPU
4. ✅ CI/CD documentation covers common platforms
5. ✅ Automatic fallback from GPU → software → Playwright
6. ✅ Performance warnings when using software rendering

## Related Issues

- Issue 102: Architectural disconnect (fallback to Playwright)
- Issue 103: Smoke tests (test on GPU and software rendering)
- Issue 107: Documentation overhaul (install guides)

## Priority Justification

**HIGH** (not CRITICAL) because:
- Blocks CI/CD adoption
- Affects user onboarding experience
- Required for production deployment
- But: workaround exists (run in environment with GPU)
- Not blocking core development (can develop on machines with GPU)
