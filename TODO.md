# Vexy Stax PY - TODO List

## Phase 1: Core Browser Automation

### Browser Setup
- [ ] Install playwright as dependency
- [ ] Add playwright to pyproject.toml
- [ ] Create `src/vexy_stax/browser.py`
- [ ] Implement `VexyStaxBrowser` class
  - [ ] `__init__()` with headless/url params
  - [ ] `async launch()` method
  - [ ] `async close()` method
- [ ] Add browser launch tests
- [ ] Document browser automation in README

### Image Loading
- [ ] Implement `async load_images()` method
- [ ] Use Playwright file chooser API
- [ ] Wait for imageStack via console API
- [ ] Add error handling for missing files
- [ ] Test with 1, 3, 10 images
- [ ] Handle timeout scenarios

### Scene Control
- [ ] Implement `async set_z_spacing()` method
- [ ] Implement `async set_camera_mode()` method
- [ ] Implement `async apply_material()` method
- [ ] Implement `async set_background()` method
- [ ] Test each control method
- [ ] Add integration tests

### Export Control
- [ ] Implement `async export_png()` method
- [ ] Handle download completion
- [ ] Verify exported files
- [ ] Test 1x, 2x, 4x scales
- [ ] Add export timeout handling

---

## Phase 2: Fire CLI Interface

### CLI Structure
- [ ] Create `src/vexy_stax/cli.py`
- [ ] Add fire dependency
- [ ] Create `VexyStaxCLI` class
- [ ] Add `generate_test()` command
- [ ] Add `launch()` command
- [ ] Add `export()` command
- [ ] Add `animate()` command
- [ ] Update entry point in pyproject.toml

### Command Implementation
- [ ] Implement `generate_test()` with args
  - [ ] `--output-dir` for custom directory
  - [ ] `--count` for number of images
  - [ ] `--size` for image dimensions
- [ ] Implement `launch()` with args
  - [ ] `--images` for image paths
  - [ ] `--url` for custom app URL
  - [ ] `--headless` for headless mode
- [ ] Implement `export()` with args
  - [ ] `--config` for JSON config path
  - [ ] `--scale` for export resolution
  - [ ] `--output` for output path
- [ ] Implement `animate()` with args
  - [ ] `--config` for JSON config
  - [ ] `--duration` for animation length
  - [ ] `--output` for video path

### Configuration Support
- [ ] Define JSON schema for configs
- [ ] Create `src/vexy_stax/config.py`
- [ ] Implement `load_config()` function
- [ ] Implement `save_config()` function
- [ ] Validate config structure
- [ ] Add config examples to `examples/`
- [ ] Test config loading/saving

---

## Phase 3: Video Capture System

### Screenshot Capture
- [ ] Create `src/vexy_stax/capture.py`
- [ ] Implement `capture_screenshot()` method
- [ ] Handle viewport scaling
- [ ] Support custom dimensions
- [ ] Test high-res captures
- [ ] Add screenshot tests

### Animation Recording
- [ ] Implement `VideoCapture` class
- [ ] Implement `async record_animation()` method
- [ ] Capture frames at 60 FPS
- [ ] Store frames efficiently
- [ ] Add progress indicator
- [ ] Test frame capture accuracy

### Video Encoding
- [ ] Add ffmpeg-python dependency
- [ ] Implement `encode_video()` method
- [ ] Support WebM format (VP9 codec)
- [ ] Support MP4 format (H.264 codec)
- [ ] Add video quality settings
- [ ] Test encoding with various frame counts
- [ ] Handle encoding errors gracefully

---

## Phase 4: Code Cleanup & Migration

### Remove Validation Code
- [ ] Delete `src/vexy_stax/validate_output.py`
- [ ] Delete `tests/test_validate_output.py`
- [ ] Update pyproject.toml (remove validation scripts)
- [ ] Update README (remove validation sections)
- [ ] Remove img/ directory references

### Refactor Test Images
- [ ] Rename `create_test_images.py` → `test_images.py`
- [ ] Update function name to `generate_test_images()`
- [ ] Add more test image options (sizes, colors)
- [ ] Keep CLI command as `generate-test`
- [ ] Update tests

### Create Examples
- [ ] Create `examples/` directory
- [ ] Write `examples/basic_usage.py`
- [ ] Write `examples/video_export.py`
- [ ] Write `examples/batch_processing.py`
- [ ] Write `examples/config_example.json`
- [ ] Test all examples

---

## Phase 5: Build Scripts & Documentation

### Build Scripts
- [ ] Create `build.sh` script
  - [ ] Install Playwright browsers
  - [ ] Build package with uv
  - [ ] Run tests
  - [ ] Display success message
- [ ] Make build.sh executable
- [ ] Test build script on clean system
- [ ] Add build instructions to README

### Installation Script
- [ ] Create `scripts/install_playwright.sh`
- [ ] Handle Playwright browser installation
- [ ] Add platform detection (Linux/macOS/Windows)
- [ ] Document installation steps

### Documentation
- [ ] Update README.md
  - [ ] Remove validation-focused content
  - [ ] Add browser automation docs
  - [ ] Add CLI usage examples
  - [ ] Add video capture examples
  - [ ] Add build/deploy instructions
- [ ] Write API documentation
- [ ] Add troubleshooting section
- [ ] Document Playwright setup

---

## Phase 6: Testing

### Unit Tests
- [ ] Test image generation
- [ ] Test configuration parsing
- [ ] Test CLI argument parsing
- [ ] Achieve 80%+ coverage

### Integration Tests
- [ ] Test browser launch
- [ ] Test image loading
- [ ] Test scene controls
- [ ] Test export functionality
- [ ] Test video capture

### E2E Tests
- [ ] Test full workflow: generate → launch → export
- [ ] Test animation workflow
- [ ] Test batch processing
- [ ] Test error scenarios

---

## Phase 7: CI/CD Updates

### GitHub Actions
- [ ] Update ci.yml workflow
  - [ ] Install Playwright
  - [ ] Run new tests
  - [ ] Build package
- [ ] Update release.yml workflow
  - [ ] Build with new dependencies
  - [ ] Test before release
- [ ] Add Playwright browser caching

### Dependencies
- [ ] Update pyproject.toml
  - [ ] Add playwright
  - [ ] Add fire
  - [ ] Add ffmpeg-python (optional)
  - [ ] Add pytest-asyncio (dev)
  - [ ] Add pytest-playwright (dev)
- [ ] Pin dependency versions
- [ ] Document dependency rationale

---

## Completed
- [x] Create PLAN.md
- [x] Create TODO.md
- [x] Keep test image generation (already works)

---

## Priority Order

**Immediate (Week 1)**:
1. Phase 1: Core Browser Automation
2. Phase 2: Fire CLI Interface
3. Phase 4: Code Cleanup

**Near-term (Week 2)**:
4. Phase 3: Video Capture System
5. Phase 5: Build Scripts & Documentation

**Future**:
6. Phase 6: Comprehensive Testing
7. Phase 7: CI/CD Updates

---

## Notes

- Focus on **browser automation** as core objective
- Remove all validation-related code
- Keep test image generation (it's useful)
- Use async/await throughout for Playwright
- Fire CLI for simple, intuitive commands
- Video capture is bonus feature (Phase 3)

---

**Status**: Planning complete. Ready to start Phase 1 implementation.
