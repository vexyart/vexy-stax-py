---
this_file: WORK.md
---

# Vexy Stax PY - Work Progress

## Current Status (2025-12-22)

- **Tests**: 115 pass, 4 skip
- **Default**: pygfx backend (playwright optional via `[browser]`)
- **GPU flags**: `--require-gpu` rejects software rendering

## JS Bugs Fixed (2025-12-22) - Verify in Python

Two bugs were fixed in the JS implementation. Python verification needed:

### 1. Ambience Y-Jump Bug
**JS Fix**: Material `side` property consistency (`FrontSide` everywhere)
**Python check**: Verify pygfx material settings don't cause position shifts during ambience changes

### 2. Hero Viewpoint Layer Depth
**JS Fix**: Added `restoreSlideZPositions()` when switching away from Hero viewpoint
**Python check**: Verify hero animation doesn't permanently collapse z-positions

## Ready for Release

- Awaiting PyPI publish after verification
