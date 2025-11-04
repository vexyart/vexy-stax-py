# Changelog

All notable changes to vexy-stax project will be documented in this file.

## [Unreleased] - 2024-11-04 Session 2

### Fixed - Maintenance Audit (2025-11-04)
- `create_test_images.py` now catches `OSError` when loading Helvetica before falling back to the default PIL font, removing the bare `except` and keeping Ruff checks clean.

### Added - Quality Improvements (Round 10)
- **Memory usage warnings** (vexy-stax-wt)
  - Tracks estimated texture memory (4 bytes per pixel)
  - Warning toast at 500MB: "⚠️ High memory usage"
  - Critical confirmation dialog at 1GB before loading more
  - Memory display in FPS counter when enabled
  - 30-second cooldown to prevent warning spam
  - Called before add (with cancel option) and after delete
  - Implementation: calculateMemoryUsage() (12 lines), checkMemoryUsage() (41 lines)

- **File type validation** (vexy-stax-wt)
  - Validates MIME types before processing
  - Supported: image/png, jpeg, jpg, gif, webp, svg+xml
  - Error toast with extension: "❌ Unsupported file type: .xyz"
  - Filters invalid files from multi-file drops
  - Summary logging of accepted/rejected counts
  - Applied to both file input and drag-drop
  - Implementation: validateImageFile() (22 lines)

- **Keyboard navigation for image list** (vexy-stax-wt)
  - Tab to focus list items (tabIndex=0)
  - Arrow Up/Down to navigate between images
  - Delete/Backspace to remove focused image (with confirmation)
  - Enter to highlight image in 3D view (green flash animation)
  - Visual focus indicator (2px green outline)
  - Focus management after deletion
  - ARIA labels for screen readers
  - Implementation: handleImageListKeydown() (61 lines), updateImageList() enhanced (+21 lines)

### Added - Quality Improvements (Round 9)
- **FPS counter and performance monitor** (vexy-stax-wt)
  - Lightweight FPS display in top-right corner
  - Toggle via window.vexyStax.showFPS(true/false)
  - Color-coded: green (good), orange (moderate), red (poor)
  - Shows current FPS and 5-second rolling average
  - Console warnings if FPS consistently below 30
  - Integrated into vexyStax.getStats() API
  - Hidden by default, no performance impact when disabled
  - Implementation: main.js:590-672 (83 lines)

- **Undo/redo functionality** (vexy-stax-wt)
  - History stack with max 10 states
  - Ctrl/Cmd + Z: Undo last change
  - Ctrl/Cmd + Shift + Z: Redo
  - Tracks add, delete, clear operations
  - Toast notifications for user feedback
  - Exposed via window.vexyStax.undo() and redo()
  - Updated keyboard shortcuts help overlay
  - Implementation: main.js:678-785 (108 lines), saveHistory() calls added

- **Export verification and confirmation** (vexy-stax-wt)
  - Verifies PNG data generation succeeded
  - Calculates and displays file size
  - Success toast: "✓ Exported: filename.png (X.XX MB)"
  - Error toast if export fails with reason
  - Detailed console logging (dimensions, size)
  - Try/catch wrapping for error detection
  - Implementation: exportPNG() enhanced (26 lines)

- **Toast notification system** (vexy-stax-wt)
  - Reusable showToast() function
  - Four types: success, error, warning, info
  - Color-coded background and text
  - Auto-dismiss with configurable duration
  - Slide-in/out animations
  - Bottom-right positioning
  - Implementation: main.js:793-828 (36 lines)

### Added - Quality Improvements (Round 8)
- **Window resize debouncing** (vexy-stax-wt)
  - Debounces window resize events with 150ms delay
  - Prevents excessive recalculations during resize
  - Cancels pending resizes when new resize occurs
  - Final resize always executes after delay
  - ~90% reduction in resize calculations
  - Implementation: main.js:464-487 (24 lines)

- **Image load retry logic** (vexy-stax-wt)
  - Automatic retry with exponential backoff
  - Max 3 attempts: 500ms, 1500ms, 3000ms delays
  - Logs each retry attempt
  - Success message on retry success
  - Clear error after all retries exhausted
  - Resilient to network hiccups
  - Implementation: loadImage() enhanced (54 lines)

- **WebGL context loss recovery** (vexy-stax-wt)
  - Handles GPU resets gracefully
  - 'webglcontextlost' listener prevents default
  - 'webglcontextrestored' reinitializes renderer
  - Reloads all textures automatically
  - Shows orange "recovering..." message during loss
  - Shows green "recovered" message for 3s after restore
  - Zero downtime from GPU resets
  - Implementation: main.js:492-570 (79 lines)

### Added - Quality Improvements (Round 7)
- **localStorage error recovery** (vexy-stax-wt)
  - Enhanced saveSettings() with QuotaExceededError detection
  - User-friendly confirm dialog when storage quota exceeded
  - Automatic clear and retry with user confirmation
  - Graceful fallback if storage unavailable
  - Implementation: main.js:334-386 (enhanced)

- **Debug console API** (vexy-stax-wt)
  - Exposed window.vexyStax object with public API
  - Functions: exportPNG(scale), clearAll(), reset/load/saveSettings()
  - getImageStack() returns detailed image info array
  - getStats() shows memory usage, pixel count, settings
  - help() displays styled console documentation
  - Green-highlighted init message
  - Implementation: main.js:302-402 (106 lines)

- **Proper resource cleanup** (vexy-stax-wt)
  - beforeunload event handler for memory leak prevention
  - Disposes all geometries, materials, textures
  - Disposes OrbitControls and renderer
  - Forces WebGL context loss
  - Clears scene and imageStack
  - Wrapped in try/catch for safety
  - Implementation: main.js:407-459 (55 lines)

### Added - Quality Improvements (Round 6)
- **Keyboard shortcuts** (vexy-stax-wt)
  - Ctrl/Cmd + E: Export PNG at 1x resolution
  - Ctrl/Cmd + Delete: Clear all images (with confirmation)
  - ? key: Toggle keyboard shortcuts help overlay
  - Esc key: Close help overlay
  - Help overlay displays styled table of all shortcuts
  - Implementation: main.js:199-291 (93 lines)

- **Settings persistence** (vexy-stax-wt)
  - Automatic save/load using localStorage
  - Persisted settings: cameraMode, cameraFOV, cameraZoom, bgColor, transparentBg, zSpacing
  - Added "Reset to Defaults" button in Tweakpane
  - Graceful fallback when localStorage unavailable
  - Settings load on init, save on every change
  - Implementation: main.js:297-385 (89 lines)

- **Export progress indicator** (vexy-stax-wt)
  - Loading overlay for high-resolution exports (2x, 3x, 4x)
  - Shows "Exporting... Rendering at ${scale}x resolution"
  - Full-screen semi-transparent overlay
  - Uses setTimeout to allow UI update before render
  - No overlay for 1x exports (near-instant)
  - Implementation: exportPNG() enhanced (47 lines)

### Added - vexy-stax-wl Planning Phase
- Created comprehensive React/R3F implementation plan (PLAN.md, 25KB, 500+ lines)
- Created 70+ itemized tasks (TODO.md)
- Created package dependency justifications (DEPENDENCIES.md, 10KB)
- Created planning documentation (WORK.md, CHANGELOG.md, README.md)
- **Critical finding**: Leva is React-only, requires complete architectural rewrite

### Added - Documentation (Round 4)
- Created project-level README.md explaining multi-project structure
- Added vexy-stax-wt vs vexy-stax-wl comparison tables
- Added decision guide for choosing between variants
- Created comprehensive vexy-stax-wl/README.md documenting planning phase status

### Added - Quality Improvements (Round 5)
- **WebGL capability detection** (vexy-stax-wt)
  - Added detectCapabilities() function to check WebGL, FileReader, Canvas.toDataURL APIs
  - Shows styled error modal if browser lacks required features
  - Prevents silent failures on unsupported browsers
  - Implementation: main.js:33-90

- **Input validation for images** (vexy-stax-wt)
  - File size validation: warns at 10MB, rejects at 50MB
  - Image dimension validation: warns if >4096px
  - User-friendly confirmation dialogs for large files
  - Graceful error handling with helpful messages
  - Implementation: main.js:687-742

- **Visual regression testing**
  - Created test-img/reference/ directory with baseline images
  - Added PIL-based pixel comparison to test.sh
  - 1% pixel difference threshold with 10-unit RGB tolerance per channel
  - Automatically detects rendering regressions
  - Tests: 7→8 total tests, all passing

### Fixed - Test Suite (Round 3)
- Fixed test.sh hanging issue (removed tests for non-existent directories)
- Simplified from 158 to 137 lines initially
- Enhanced with visual regression test (+56 lines)
- All 8 tests now pass reliably in <1 second

### Verified
- vexy-stax-wt Tweakpane UI confirmed working (false alarm in TODO)
- vexy-stax-pm 3D rendering confirmed fixed (previous session)
- All browser capabilities properly detected and validated
- Visual output consistency maintained across changes
- Final test suite run: 8/8 tests passing in <1 second (2024-11-04)

## [Unreleased] - 2024-11-04 Session 1

### Added - New Projection Modes
- **vertical_stack projection**: Layers stack UPWARD along vertical viewport edge
  - Z-axis maps to Y-axis (vertical) screen movement
  - Implemented in vexy-stax-pc and vexy-stax-pm
  - Formula: `u = x, v = -(z + 0.3*y)` for viewport-aligned stacking

- **horizontal_stack projection**: Layers stack SIDEWAYS along horizontal viewport edge
  - Z-axis maps to X-axis (horizontal) screen movement
  - Implemented in vexy-stax-pc and vexy-stax-pm
  - Formula: `u = z + 0.3*x, v = y` for viewport-aligned stacking

### Added - Quality Improvements Round 2
- **Path resolution enhancement**: All run.py scripts now resolve paths relative to config.json location
  - Can execute from any directory
  - Paths resolve correctly regardless of cwd
  - Output directories created automatically

- **Example configurations**: 11 comprehensive example configs across pc and pm implementations
  - vexy-stax-pc: 4 examples (orthographic, isometric, vertical_stack, horizontal_stack)
  - vexy-stax-pm: 7 examples (adds isometric_45, perspective, perspective_wide)
  - Each example includes detailed descriptions and documentation
  - README.md files explain when to use each projection mode

- **Test automation script**: test.sh at project root
  - 4 test suites: core functionality, pc projections, pm viewpoints, browser tests
  - PNG validation using PIL
  - Config backup/restore functionality
  - Color-coded pass/fail output
  - Timeout handling for browser tests

### Added - Quality Improvements Round 1
- **Config standardization**: Unified output path structure across all projects
  - Changed from flat `"output": "path"` to nested `"output": {"path": "...", "width": ..., "height": ...}`
  - All projects now use consistent format

- **Config validation**: Added validate_config() to all run.py scripts
  - JSON schema validation
  - Required field checking
  - File existence verification
  - Clear error messages

- **Output validation**: Created validate_output.py tool
  - Validates PNG format
  - Checks dimensions
  - Verifies file integrity
  - Reports size and color mode

### Added - Test Infrastructure
- **Colored test layers**: Created layer1.png (red), layer2.png (cyan), layer3.png (yellow)
  - 400x300 px colored rectangles in test-img/
  - Makes stacking visualization immediately obvious
  - Used in all projection mode examples

- **Output validation tool**: validate_output.py
  - Uses PIL to verify PNG integrity
  - Checks all project outputs
  - Reports dimensions, mode, file size

### Testing
- All 4 implementations tested and passing:
  - vexy-stax-pc: ✓ (800x600, RGB, 26KB)
  - vexy-stax-pm: ✓ (800x600, RGBA, 51KB)
  - vexy-stax-wl: ✓ (800x600, RGB, 12KB)
  - vexy-stax-wt: ✓ (800x600, RGB, 6KB)

- New projection modes tested:
  - vertical_stack (pc): ✓
  - horizontal_stack (pc): ✓
  - vertical_stack (pm): ✓
  - horizontal_stack (pm): ✓

- Example configs tested:
  - All 11 example configurations verified working

- Path resolution tested:
  - Execution from different directories verified
  - Relative path resolution confirmed

### Changed
- Updated run.py in vexy-stax-pc to use config_path.parent.resolve() for base directory
- Updated run.py in vexy-stax-pm to use config_path.parent.resolve() for base directory
- Modified cli.py in vexy-stax-pc to include new projection functions
- Extended PROJECTIONS dict with vertical_stack and horizontal_stack
- Extended Viewpoint presets in vexy-stax-pm with new stacking modes

### Technical Details

**Projection Mathematics**:
- vertical_stack uses side-view transform: Z→Y (negative for upward), X→X
- horizontal_stack uses rotated top-down: Z→X, Y→Y
- Both include 0.3 coefficient for subtle depth perception
- Scale parameter properly applied in all projections

**Path Resolution**:
- Uses pathlib.Path for cross-platform compatibility
- .resolve() provides absolute paths
- Relative paths interpreted from config.json location
- Output directories created with parents=True, exist_ok=True

**Example Structure**:
- Each example is self-contained JSON file
- Includes description field explaining the projection
- Uses relative paths to test images
- Specifies output dimensions
- README.md provides usage instructions and projection explanations
