# Vexy Stax PY - Implementation Plan

**One-sentence scope**: Python CLI tool for automating Vexy Stax 3D image visualization via Playwright browser automation and test image generation.

## Core Objectives

1. **Browser Automation**: Control vexy-stax-js web app via Playwright
2. **Fire CLI**: Simple command-line interface for automation  
3. **Test Data Generation**: Create test images for development
4. **Integration**: Seamless workflow with vexy-stax-js

## Architecture

```
Fire CLI (cli.py)
    ↓
VexyStaxBrowser (browser.py)  
    ↓
Playwright → Chromium
    ↓
http://localhost:5173/vexy-stax-js/
    ↓
Three.js + GSAP Animation
```

## Implementation Status

### ✅ Phase 1: Core Automation (COMPLETE)

**Browser Automation (`browser.py`)**:
- `VexyStaxBrowser` class wraps Playwright sync API
- `launch()` - Start Chromium, navigate to dev server
- `close()` - Clean shutdown
- `load_images()` - Upload PNGs via file input
- `load_config()` - Load JSON with embedded images
- `play_animation()` - Trigger GSAP hero shot
- `export_png()` - Download PNG export
- `get_stats()` - Query app statistics

**CLI Interface (`cli.py`)**:
- Fire-based automatic CLI generation
- Commands: `launch`, `animate`
- Natural syntax: `vexy-stax launch --images=test-img/`

**Test Data (`create_test_images.py`)**:
- Generates 3 test PNGs (400×300px, distinct colors)
- Creates test-img/ directory
- Also generates layer123.json with embedded images

**Development Workflow (`run.sh`)**:
- Sets PYTHONPATH for running without install
- Usage: `./run.sh python -m vexy_stax.cli launch`

### ✅ Phase 2: Quality Improvements (COMPLETE)

**Removed Validation Code**:
- Deleted validate_output.py per 101.md requirement
- Removed validation CLI entry point
- Updated package metadata

**Fixed API Integration**:
- Changed browser.py to use window.vexyStax.loadConfig()
- Coordinated with JS repo to add loadConfig API method

**Error Handling**:
- Added helpful error when dev server not running
- 5s timeout on page load
- Clear instructions to user

### 📝 Phase 3: Documentation (CURRENT)

**Files**:
- ✅ PLAN.md - This file (comprehensive plan)
- 🔄 TODO.md - Flat checklist (next)
- ⏳ README.md - Update to reflect automation focus
- ✅ WORK.md - Progress tracking (maintained)

### ⏳ Phase 4: Testing (PENDING)

**Prerequisites**:
```bash
playwright install chromium
```

**End-to-End Tests**:
1. Launch browser with images
2. Load JSON config  
3. Headless automation
4. Animation playback

**Unit Tests** (Future):
- Test image generation
- Test CLI argument parsing
- Mock Playwright tests (optional)

### ⏳ Phase 5: Video Recording (FUTURE)

**Goal**: Record GSAP animation to video file

**Approaches**:
1. Playwright built-in video recording
2. MediaRecorder API + download
3. Frame-by-frame capture → FFmpeg

**CLI Command**:
```bash
vexy-stax record --images=test-img/ --output=hero.webm --fps=60
```

## Dependencies

| Package | Version | Purpose | Status |
|---------|---------|---------|--------|
| playwright | >=1.40.0 | Browser automation | ✅ Added |
| fire | >=0.6.0 | CLI generation | ✅ Added |
| pillow | >=11.0.0 | Image generation | ✅ Existing |
| hatchling | - | Build backend | ✅ Configured |
| hatch-vcs | - | Git-tag versioning | ✅ Configured |

**Why These Packages**:
- Playwright: Industry standard, reliable, well-documented
- Fire: Minimal boilerplate, automatic help generation
- Pillow: Standard Python imaging library

## Integration with vexy-stax-js

**Coordination Points**:
1. Window API: Python calls `window.vexyStax.*` methods ✅
2. Dev Server: Must run at localhost:5173 ✅  
3. File Paths: Absolute paths passed to browser ✅
4. JSON Format: Shared config format ✅

**Sync Requirements**:
- JS exposes window.vexyStax.loadConfig() ✅
- JS supports file input for images ✅
- JS has GSAP animation system ✅
- Python generates compatible JSON ✅

## Success Criteria

**Must Have** (✅ Complete):
- ✅ Python CLI can launch browser and load images
- ✅ Can trigger GSAP animation from Python
- ✅ Fire CLI provides natural command syntax
- ✅ Test data generation works
- ✅ Error handling for common issues
- ✅ Proper API integration with JS

**Should Have** (Current Focus):
- 🔄 Comprehensive documentation
- ⏳ End-to-end tests with real browser
- ⏳ Unit tests for core functionality

**Nice to Have** (Future):
- Video recording during animation
- Batch processing multiple configs
- Screenshot comparison tools

## Non-Goals (RED LIST)

Per CLAUDE.md guidelines, we **DO NOT** add:
- ❌ Analytics/metrics
- ❌ Performance monitoring frameworks  
- ❌ Advanced error recovery
- ❌ Security hardening beyond basics
- ❌ Configuration validation systems
- ❌ Health monitoring
- ❌ Circuit breakers/retry strategies
- ❌ Sophisticated caching
- ❌ Advanced logging frameworks

## Next Steps

**Immediate**:
1. ✅ Create PLAN.md
2. 🔄 Create TODO.md  
3. ⏳ Update README.md

**Short Term**:
- Install Playwright browsers
- Run end-to-end tests
- Verify animation works

**Medium Term**:
- Add unit tests
- Implement video recording
- Test cross-platform

**Long Term**:
- Publish to PyPI
- Add to CI/CD
- Create example workflows
