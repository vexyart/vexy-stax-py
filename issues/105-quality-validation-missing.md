---
this_file: issues/105-quality-validation-missing.md
priority: HIGH
category: Quality Assurance
created: 2025-11-06
---

# Issue 105: No Quality Validation Framework to Verify Pygfx Output Matches JS

## Problem Statement

Project goal (issues/101.md) is to replicate vexy-stax-js rendering with pygfx, but **zero validation** exists to verify output quality. Users have no confidence pygfx renders match the JavaScript version. No regression detection if quality degrades.

## Core Issue: Trust Gap

From user perspective:
1. JS version produces beautiful renders
2. Python version claims parity
3. **How do I verify they match?**
4. **What if I ship to client and quality is wrong?**

Currently: 🤷 Hope it works

## What Quality Means

### Visual Fidelity Components
1. **Color accuracy**: RGB values match within tolerance
2. **Material appearance**: Glossy/matte/metal looks similar
3. **Lighting**: Shadows, highlights, reflections comparable
4. **Geometry**: Layer spacing, sizing, positioning correct
5. **Camera framing**: FOV, perspective, orthographic match
6. **Transparency handling**: Alpha blending correct
7. **Background rendering**: Solid/transparent as configured
8. **Animation paths**: Hero shot camera movement identical

### Current State: Unknown
- Materials implemented (`renderer/materials.py`) but **never compared to JS**
- Camera logic exists (`renderer/camera.py`) but **never validated against JS**
- Export works (`renderer/export.py`) but **never checked for visual match**

## Required Validation Framework

### Level 1: Pixel-Perfect Comparison (Baseline)
```python
# tests/test_visual_regression.py

def test_identical_scenes_produce_similar_output():
    """Compare pygfx render to JS reference for same scene."""

    scene_json = Path("test-img/layer123.json")

    # Render with pygfx
    pygfx_output = render_with_pygfx(scene_json, width=800, height=600)

    # Load JS reference (pre-rendered)
    js_reference = Path("test-img/reference-renders/layer123-800x600.png")

    # Compare
    comparison = compare_images(pygfx_output, js_reference)

    # Assertions
    assert comparison.pixel_match > 0.98, "98% pixels must match"
    assert comparison.mae < 5.0, "Mean Absolute Error < 5 RGB units"
    assert comparison.ssim > 0.95, "Structural Similarity > 0.95"

    # Save diff if failed
    if comparison.pixel_match < 0.98:
        comparison.save_diff("test-failures/layer123-diff.png")
```

### Level 2: Perceptual Quality Metrics
```python
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def compare_images(test_img: Path, reference_img: Path) -> ImageComparison:
    """Compare two images using multiple quality metrics."""

    test = load_image_as_rgb(test_img)
    ref = load_image_as_rgb(reference_img)

    # Pixel-level metrics
    mae = np.mean(np.abs(test - ref))  # Mean Absolute Error
    mse = np.mean((test - ref) ** 2)   # Mean Squared Error

    # Perceptual metrics
    ssim_score = ssim(ref, test, channel_axis=2)
    psnr_score = psnr(ref, test)

    # Histogram comparison
    hist_correlation = compare_histograms(ref, test)

    # Alpha channel specific (if present)
    alpha_match = None
    if test.shape[2] == 4:
        alpha_match = np.mean(test[:, :, 3] == ref[:, :, 3])

    return ImageComparison(
        pixel_match=1.0 - (mae / 255.0),
        mae=mae,
        mse=mse,
        ssim=ssim_score,
        psnr=psnr_score,
        histogram_correlation=hist_correlation,
        alpha_match=alpha_match,
    )
```

### Level 3: Component-Specific Validation
```python
def test_material_preset_matte_matches_js():
    """Validate matte material renders similarly to JS."""

    scene = create_test_scene(
        images=[solid_color_image(255, 0, 0)],  # Pure red
        material="flat-matte",
        lighting="ambient-only"
    )

    pygfx_render = render_with_pygfx(scene)
    js_reference = load_js_reference("matte-red-ambient.png")

    # Matte should have no specular highlights
    assert has_no_specular_highlights(pygfx_render)
    assert color_matches(pygfx_render, (255, 0, 0), tolerance=10)
    assert visual_similarity(pygfx_render, js_reference) > 0.95

def test_material_preset_glossy_has_highlights():
    """Validate glossy material renders with specular highlights."""

    scene = create_test_scene(
        images=[solid_color_image(0, 0, 255)],  # Pure blue
        material="glossy-photo",
        lighting="three-point"
    )

    render = render_with_pygfx(scene)

    # Glossy should have visible highlights (brighter pixels)
    max_value = render.max(axis=(0, 1))
    assert max_value[2] > 200, "Should have bright blue highlights"
    assert has_specular_highlights(render)
```

### Level 4: Animation Consistency
```python
def test_hero_animation_camera_path_matches_js():
    """Validate animation produces same camera positions."""

    scene = load_scene("test-img/layer123.json")

    # Render key frames with both
    pygfx_frames = render_hero_animation(scene, backend="pygfx")
    js_reference_frames = load_js_reference_frames("layer123-hero/")

    for i, (pygfx_frame, js_frame) in enumerate(zip(pygfx_frames, js_reference_frames)):
        similarity = visual_similarity(pygfx_frame, js_frame)
        assert similarity > 0.93, f"Frame {i} similarity {similarity} < 0.93"
```

## Reference Image Generation

### Problem: Need JS-Rendered References
Can't validate without known-good JS outputs

### Solution 1: Pre-Generate Reference Set
```bash
# In vexy-stax-js project
npm run dev

# Render reference scenes
for scene in test-scenes/*.json; do
  vexy-stax-js render --scene $scene --output refs/$(basename $scene .json).png
done

# Copy to Python project
cp refs/* vexy-stax-py/tests/fixtures/reference-renders/
```

### Solution 2: Live Comparison Mode
```bash
# Start JS dev server
cd vexy-stax-js && npm run dev

# Python renderer connects to JS to generate reference on-the-fly
vexy-stax test-quality --scene test.json --compare-to-js

# Process:
# 1. Python renders with pygfx → output1.png
# 2. Python instructs JS (via Playwright) to render same scene → output2.png
# 3. Compare output1 vs output2
# 4. Report differences
```

## Acceptance Thresholds

Based on research of rendering quality validation:

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Pixel Match | > 98% | Allow minor anti-aliasing differences |
| SSIM | > 0.95 | Structural similarity index |
| MAE | < 5.0 | Mean Absolute Error (RGB 0-255 scale) |
| PSNR | > 35 dB | Peak Signal-to-Noise Ratio |
| Histogram Correlation | > 0.98 | Color distribution match |

**Adjustable per test**: Some tests may be stricter (materials) vs looser (animation)

## Regression Detection

### Git-Based Reference Tracking
```
tests/
  fixtures/
    reference-renders/
      layer123-800x600-v1.0.png          ← JS render, tracked in git
      layer123-800x600-v1.0.meta.json    ← Metadata: when, how, what version
```

### Test Updates on Changes
```python
@pytest.mark.visual_regression
def test_default_scene_regression():
    """Detect if rendering changed from baseline."""

    result = render_with_pygfx("test-img/layer123.json")
    baseline = "tests/fixtures/reference-renders/layer123-baseline.png"

    comparison = compare_images(result, baseline)

    if comparison.ssim < 0.95:
        # Save failure artifacts
        result.save("test-failures/layer123-current.png")
        comparison.save_diff("test-failures/layer123-diff.png")

        pytest.fail(
            f"Visual regression detected!\n"
            f"SSIM: {comparison.ssim:.3f} (threshold: 0.95)\n"
            f"See: test-failures/layer123-diff.png"
        )
```

## User-Facing Validation Tool

### CLI Command: `vexy-stax compare`
```bash
# Compare specific renders
vexy-stax compare \
  --pygfx render1.png \
  --js-reference render2.png \
  --report comparison.html

# Interactive comparison
vexy-stax compare --interactive \
  --scene test.json \
  --backends pygfx,playwright

# Output: Side-by-side viewer with:
# - Image diff highlighting
# - Metrics table
# - Zoom/pan for inspection
# - Pass/fail criteria
```

## Implementation Plan

### Week 1: Foundation
1. Implement `compare_images()` with SSIM, MAE, PSNR
2. Create `ImageComparison` result class
3. Add basic test comparing two PNGs

### Week 2: JS Reference Pipeline
1. Document how to generate references from JS
2. Create reference scene set (5-10 canonical scenes)
3. Render all with JS, commit to `tests/fixtures/reference-renders/`
4. Add metadata files

### Week 3: Validation Tests
1. Implement pixel-perfect comparison tests
2. Add material-specific validation
3. Add animation frame comparison
4. Document acceptable thresholds

### Week 4: Tooling & CI
1. Create `vexy-stax compare` CLI tool
2. Add visual regression to CI pipeline
3. Auto-generate diff artifacts on failure
4. Add to release checklist

## Success Criteria

1. ✅ 5+ test scenes with JS reference renders
2. ✅ Visual regression tests pass for all references
3. ✅ Material presets validated individually
4. ✅ Animation frames validated for consistency
5. ✅ Quality metrics documented and justified
6. ✅ `vexy-stax compare` tool available
7. ✅ CI fails if visual regression detected

## Known Limitations & Gaps

### Expected Differences
- **Anti-aliasing**: pygfx and Three.js may use different algorithms
- **Floating-point precision**: Minor color variations due to GPU differences
- **Shader implementations**: Lighting calculations may vary slightly
- **Compression artifacts**: PNG encoding may differ

### Documented Gaps
Track known quality differences in `QUALITY.md`:
- "Metal material 5% less reflective than JS (acceptable)"
- "Glass transparency 10% opacity difference (under investigation)"
- "Shadow softness differs (pygfx limitation documented)"

## Related Issues

- Issue 103: Smoke test (quality validation builds on working render)
- Issue 102: Architectural disconnect (quality validation requires pygfx path)
- Issue 106: Video export validation (extends to animation quality)

## Priority Justification

**HIGH** because:
- Core value proposition is parity with JS
- Users need confidence in output quality
- Regression detection protects against breakage
- But: Can ship without perfect parity if documented
- Workaround: Manual visual inspection
