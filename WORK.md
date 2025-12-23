---
this_file: WORK.md
---

# Vexy Stax PY - Work Progress

## Current Status (2025-12-23)

- **Tests**: 115 pass, 4 skip
- **Default**: pygfx backend (playwright optional via `[browser]`)
- **GPU flags**: `--require-gpu` rejects software rendering

## Session 2025-12-23

### Cinematic 3-Point Lighting

**Goal**: Improve beauty view photorealism per CONTINUE.md.

**Change**: Upgraded from single directional light to 3-point lighting setup:
- Key light (warm 1.0/0.98/0.95) from upper-right at intensity 0.8
- Fill light (cool 0.95/0.97/1.0) from left at intensity 0.3
- Ambient reduced from 0.6 to 0.5 for better contrast

All lights interpolate to zero at hero culmination, preserving flat composite appearance.

**Result**: Better depth perception and cinematic quality in beauty view while hero view remains unchanged.

### Hero View Content-Fit Fix

**Problem**: Hero view didn't fill viewport - slide appeared cut off.

**Root Cause**: Camera was looking at content center (average Z of all slides) instead of front slide. With spacing=3 and 4 slides, content center was at Z=4.5 but front slide was at Z=9.

**Fix**:
1. `calculate_front_viewpoint`: Added `front_slide_index` parameter to compute correct collapse Z position (`front_slide_index * MIN_LAYER_GAP`)
2. `HeroTimeline`: Added `camera_targets` list for interpolated look-at positions
3. `build_hero_timeline`: New `start_target` parameter, interpolates camera target from content center (beauty) to front slide (hero)
4. `_render_animation_frames`: Uses timeline camera_targets instead of recalculating content_center per frame

**Result**: Hero view now perfectly content-fits the front slide (verified with 1920x1080 test scene).

### Demo Script Fix

**Problem**: demopy.sh extracted "medial" frame at video midpoint (frame 37), which is during forward animation phase (dark, transitioning).

**Fix**: Changed to extract "hero" frame at start of hold phase (frame 45) where `hero_progress=1.0`, lighting is flat, and basic material is applied.

## Ready for Release

- All tests passing (115 Python, 462 JS unit, 6/7 E2E)
- Hero view content-fit verified
- Animation ends at hero view (return_to_start=False)
