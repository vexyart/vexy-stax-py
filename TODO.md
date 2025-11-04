# Vexy Stax PY - TODO

## Phase 1: Core Automation ✅

- [x] Add Playwright dependency (>=1.40.0)
- [x] Add Fire dependency (>=0.6.0)
- [x] Create browser.py with VexyStaxBrowser class
- [x] Implement launch() method
- [x] Implement close() method
- [x] Implement load_images() method
- [x] Implement load_config() method  
- [x] Implement play_animation() method
- [x] Implement export_png() method
- [x] Implement get_stats() method
- [x] Create cli.py with Fire CLI
- [x] Add launch command
- [x] Add animate command
- [x] Create run.sh for development workflow
- [x] Update pyproject.toml with CLI entry points

## Phase 2: Quality Improvements ✅

- [x] Remove validate_output.py per 101.md
- [x] Update pyproject.toml description
- [x] Remove validation CLI entry point
- [x] Fix browser.py API call (use loadConfig)
- [x] Add error handling for dev server not running
- [x] Add 5s timeout on page load

## Phase 3: Documentation 🔄

- [x] Create PLAN.md
- [x] Create TODO.md (this file)
- [ ] Update README.md to reflect automation focus
- [ ] Remove validation references from README
- [ ] Add Playwright installation instructions
- [ ] Add usage examples for CLI commands

## Phase 3.5: Code Quality Iteration 3 ✅

- [x] Fix f-string injection in browser.py play_animation()
- [x] Improve play_animation() to wait for completion instead of timeout
- [x] Add error handling for failed downloads in export_png()

## Phase 4: Testing ⏳

- [ ] Install Playwright chromium browser
- [ ] Test: Launch browser with images
- [ ] Test: Load JSON config  
- [ ] Test: Headless automation
- [ ] Test: Animation playback
- [ ] Add unit test for create_test_images
- [ ] Add unit test for CLI argument parsing
- [ ] Document test results in WORK.md

## Phase 5: Video Recording ⏳

- [ ] Research video recording approaches
- [ ] Choose: Playwright video vs MediaRecorder vs FFmpeg
- [ ] Implement video capture module
- [ ] Add record command to CLI
- [ ] Test video recording with animation
- [ ] Add video dependencies to pyproject.toml

## Future Enhancements 📋

- [ ] Batch processing for multiple configs
- [ ] Cross-platform testing (Windows, Linux)
- [ ] Publish to PyPI
- [ ] Add to CI/CD pipeline
- [ ] Create example workflows directory
- [ ] Screenshot comparison for visual regression testing

## Phase 6.6: Code Quality Iteration 6 ✅

- [x] Add file error handling to load_config() in browser.py
- [x] Improve load_config timeout to wait for actual completion
- [x] Test all changes and verify functionality

## Phase 6.7: Code Quality Iteration 8 ✅

- [x] Add scale parameter validation to export_png() in browser.py
- [x] Add image count validation before export_png triggers download
- [x] Test all changes and verify functionality
