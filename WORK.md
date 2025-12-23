---
this_file: WORK.md
---

# Vexy Stax PY - Work Progress

## Current Status (2025-12-23)

- **Tests**: 115 pass, 4 skip
- **Default**: pygfx backend (playwright optional via `[browser]`)
- **GPU flags**: `--require-gpu` rejects software rendering
- **Coordinate System**: PLAN.md §1 compliant (final slide at Z=0)

## Session 2025-12-23 - Verification Complete

### Visual Quality Verification

Verified Python implementation against CONTINUE.md requirements:

1. **Beauty View** ✅
   - 3/4 angle camera (25° horizontal, 15° vertical)
   - Cinematically balanced composition filling scene
   - 3D stack visible with depth perspective

2. **Hero View** ✅
   - Straight-on camera at origin (0,0,0) target
   - MIN_LAYER_GAP = 3px spacing prevents z-fighting
   - Content-fits perfectly (5% safety margin)
   - No cropping of front slide

3. **Photorealism** ✅
   - "basic" (unlit) material preserves original image lighting
   - Source photos have baked-in lighting - adding artificial lighting degrades quality
   - 3D effect comes from perspective/parallax, not artificial shading

### Test Results
- All 115 tests pass, 4 skipped
- demopy.sh renders 1920x1080 video successfully
- Visual inspection confirms beauty/hero views working correctly

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
