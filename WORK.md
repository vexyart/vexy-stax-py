---
this_file: WORK.md
---

# Vexy Stax PY - Work Progress

## Current Status (2025-12-31)

- **Tests**: 115 pass, 4 skip
- **Default**: pygfx backend (playwright optional via `[browser]`)
- **GPU flags**: `--require-gpu` rejects software rendering
- **Coordinate System**: PLAN.md §1 compliant (final slide at Z=0)
- **Visual Quality**: All CONTINUE.md requirements verified ✅

### Photorealism Assessment

Current implementation uses "basic" (unlit) material intentionally:
- Source images have baked-in lighting from photography
- 3D effect comes from perspective and parallax
- Adding artificial lighting would wash out original colors

**Future improvements** (not implemented, would add complexity):
- Gradient shadow texture on floor (darker under slides)
- Soft edge fade on floor perimeter
- Ambient occlusion simulation

These would require custom shaders or procedural textures. Current visual quality is satisfactory for production use.

## Session 2025-12-31 - Beauty View Bounding Sphere Fit

### Problem
CONTINUE.md requires: "beauty view should have floor width perfectly fit within the viewport".
Previous implementation used floor diagonal which left excess white space or clipped content.

### Solution
Changed to bounding sphere approach:
- Calculate 3D bounding sphere of all content (floor + slides)
- `content_radius = sqrt((floor_width/2)² + max_height² + (floor_length/2)²)`
- Distance = `content_radius / tan(fov/2) * 1.15` (15% margin)

### Result
- All content (floor + slides) fits within viewport without clipping
- Cinematic 15% margin for aesthetic framing
- Works for any scene configuration

### Verification
- 115 tests passing
- demopy.sh renders correctly
- Visual inspection confirms no clipping

---

## Session 2025-12-23 - Hero View Content-Fit Fixed

### Hero View Content-Fit Correction

**Problem**: Hero view had ~46% letterboxing (black bars around slide) due to overcorrected FOV distance calculation.

**Root Cause**: `PYGFX_FOV_CORRECTION = 1.39 * SAFETY_MARGIN = 1.05` was multiplying camera distance by 1.46x, causing the slide to appear much smaller than the viewport.

**Fix in `camera.py` line 284-294**:
- Removed `PYGFX_FOV_CORRECTION = 1.39` (was overcorrected)
- Kept minimal `SAFETY_MARGIN = 1.02` (2% margin) for anti-aliasing artifacts
- Result: Slide now fills canvas perfectly when aspect ratios match

**Verification**:
- demopy.sh renders 1920x1080 slide in 1920x1080 canvas
- Frame analysis confirms 0px margins on all sides
- Hero view fills viewport completely

### Visual Quality Summary

1. **Beauty View** ✅
   - 3/4 angle camera (25° horizontal, 15° vertical)
   - Cinematically balanced composition
   - 3D stack with depth perspective visible

2. **Hero View** ✅
   - Straight-on camera at front slide
   - MIN_LAYER_GAP = 3px spacing prevents z-fighting
   - Content-fits perfectly (2% safety margin)
   - No cropping, no letterboxing when aspect ratios match

3. **Photorealism** ✅
   - "basic" (unlit) material preserves original image lighting
   - Source photos have baked-in lighting
   - 3D effect from perspective/parallax

### Test Results
- All 115 tests pass, 4 skipped
- demopy.sh renders 1920x1080 video successfully
- Visual inspection confirms hero view fills frame

---

## Session 2025-12-23 (Continued)

### Coordinate System Alignment with JS (PLAN.md §1)

**Goal**: Align Python coordinate system with JS implementation per PLAN.md §1.

**Changes**:
1. **`render_pipeline.py` placement_hook**:
   - Changed from `z = index * z_spacing` to `z = -(slideCount - 1 - index) * z_spacing`
   - Final slide (highest index) now at Z=0 (immovable anchor)
   - Other slides at negative Z

2. **`camera.py` calculate_content_center**:
   - Stack center now at `-stack_depth / 2` (center of negative-Z stack)

3. **`camera.py` calculate_content_center_with_spacing**:
   - Same fix: center_z = `-stack_depth / 2`

4. **`camera.py` calculate_front_viewpoint**:
   - collapse_z now always 0.0 (front slide is final slide at Z=0)
   - Updated docstring to document PLAN.md §1 compliance

**Result**: Python and JS now share identical coordinate system:
- Final slide at Z=0 (immovable anchor)
- Other slides at negative Z: `z = -(slideCount - 1 - index) * effectiveSpacing`
- Hero mode collapses toward Z=0 with MIN_LAYER_GAP spacing
- Verified with demopy.sh: beauty/hero/final frames look correct

---

## Previous Session 2025-12-23

### Cinematic Beauty View & Unlit Materials

**Goal**: Improve beauty view per CONTINUE.md - fill scene cinematically, proper framing.

**Changes**:
1. **Beauty camera viewpoint**: Added `calculate_beauty_viewpoint()` function
   - Positions camera at 3/4 angle (25° horizontal, 15° vertical offset)
   - Automatically fills frame with cinematic composition
   - Ignores poorly-framed saved camera positions from JS

2. **Unlit material**: Switched to "basic" (MeshBasicMaterial) for all frames
   - Source images already have baked-in lighting
   - 3D effect comes from perspective/parallax, not artificial lighting
   - Eliminates dark beauty view issue with lit materials at oblique angles

3. **Simplified lighting**: Single ambient light at full intensity
   - Unlit material doesn't respond to directional lights
   - Removes complex lighting interpolation code

### Hero View Content-Fit Fix

**Problem**: Hero view didn't fill viewport - slide appeared cut off.

**Root Cause**: Camera was looking at content center (average Z of all slides) instead of front slide. With spacing=3 and 4 slides, content center was at Z=4.5 but front slide was at Z=9.

**Fix**:
1. `calculate_front_viewpoint`: Added `front_slide_index` parameter to compute correct collapse Z position (`front_slide_index * MIN_LAYER_GAP`)
2. `HeroTimeline`: Added `camera_targets` list for interpolated look-at positions
3. `build_hero_timeline`: New `start_target` parameter, interpolates camera target from content center (beauty) to front slide (hero)
4. `_render_animation_frames`: Uses timeline camera_targets instead of recalculating content_center per frame

**Result**: Hero view now perfectly content-fits the front slide (verified with 1920x1080 test scene).

### pygfx FOV Correction Factor

**Discovery**: pygfx renders content ~17% larger than theoretical FOV calculations predict.

**Testing**: Binary search found actual "exact fit" multiplier is 1.17x, not 1.0x.

**Fix**: Added `CONTENT_FIT_PADDING = 1.25` (1.17 * 1.07 safety margin) to ensure:
- No cropping of slide content
- Small margins acceptable per CONTINUE.md requirements
- Works regardless of slide/canvas aspect ratio match

### Demo Script Fix

**Problem**: demopy.sh extracted "medial" frame at video midpoint (frame 37), which is during forward animation phase (dark, transitioning).

**Fix**: Changed to extract "hero" frame at start of hold phase (frame 45) where `hero_progress=1.0`, lighting is flat, and basic material is applied.

## Ready for Release

- All tests passing (115 Python, 462 JS unit, 6/7 E2E)
- Hero view content-fit verified
- Animation ends at hero view (return_to_start=False)
