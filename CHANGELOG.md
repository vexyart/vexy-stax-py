---
this_file: CHANGELOG.md
---

# Changelog

All notable changes to vexy-stax project will be documented in this file.

## [Unreleased] - 2025-12-23

### 2025-12-23 - Visual Quality Verification Complete
- **Beauty view**: Cinematic 3/4 angle fills frame, 3D stack with depth perspective visible
- **Hero view**: Front slide content-fits viewport perfectly with minimal margins
- **Coordinate system**: PLAN.md §1 compliant (final slide at Z=0, others at negative Z)
- **Materials**: Basic (unlit) material preserves original image lighting
- **Tests**: 115 pass, 4 skip (up from 113)
- **Verification**: demopy.sh renders 1920×1080 video (75 frames) with correct beauty/hero views

### 2025-12-22 - Camera Targeting Fix
- **Content-centered camera**: Camera now looks at content center instead of origin (0,0,0)
  - Root cause: Slides sit on floor at Y=0 with centers at Y=height/2, but camera targeted Y=0
  - Result: Slides appeared in upper half of frame with excessive space below
- **New helpers**: `calculate_content_center()`, `calculate_content_center_with_spacing()`
- **Fixed in**: `camera.py` (make_camera, calculate_front_viewpoint), `render_pipeline.py` (animation frames)
- **Tests**: 113 pass, 4 skip (updated camera test expectations)

### 2025-12-22 - Default Backend Flip
- **Default backend**: Changed CLI default from `playwright` to `pygfx`
  - `vexy-stax render` now uses headless GPU rendering by default
  - Use `--backend=playwright` for browser automation
- **Playwright optional**: Moved playwright to optional dependency
  - Install with `pip install vexy-stax[browser]` if needed
  - Helpful error message when playwright not installed
- **GPU detection flag**: Added `--require-gpu` to render/animate commands
  - Fails if only software rendering available (llvmpipe, SwiftShader)
  - Use for CI/production where hardware GPU is expected
  - Added `check_gpu_requirements()` and `SoftwareRenderingError`
- **Tests**: 113 pass, 4 skip (up from 108)
- **Type stubs**: Added `py.typed` marker for PEP 561 compliance
  - Type checkers now recognize vexy-stax as a typed package
- **Classifiers**: Added Python 3.13 and "Typing :: Typed" to pyproject.toml

### 2025-12-22 - JS Parity Porting
- **MIN_LAYER_GAP**: Added MIN_LAYER_GAP=3 constant to prevent z-fighting during hero shot
  - Hero animation now collapses to MIN_LAYER_GAP instead of 0
  - Matches JS Session 13 fix
- **Y positioning**: Slides now sit on floor (Y = height/2)
  - Bottom of slide sits on floor plane at Y=0
  - Matches JS Y positioning behavior
- **Material alignment**: Matte roughness changed from 0.9 to 0.7
  - Matches JS MATERIAL_PRESETS.matte
- **Material alias**: Added "metal-sheet" as alias for "metal" preset
- **Tests**: Updated camera and materials tests for new behavior (106 total, 102 pass, 4 skip)
- **Verification**: demopy.sh produces 1920x1080 video (1.0M, 120 frames) in 2.59s

### 2025-12-21 - Demo Scripts & Video Export Fix
- **Demo scripts**: Added `demopy.sh` (Python/pygfx) and `demojs.py` (JS/Playwright) for 1920x1080 beauty shot recordings.
- **Video export fix**: Fixed `model_copy()` bug in `_render_animation_frames` – SceneParams is a dataclass, use `dataclasses.replace()`.
- **Canvas readback fix**: Use `np.asarray(canvas.draw())` instead of `np.frombuffer(canvas._last_image)` for proper pixel reading.
- **FFmpeg plugin**: Added `imageio[ffmpeg]` dependency for H.264 video encoding.
- **Verification**: 102/102 tests passing, demo_pygfx.mp4 (287KB, 75 frames) exported successfully.

### 2025-12-21 - Phase 3 UX Complete
- **Video export CLI**: `vexy-stax animate --backend=pygfx` exports MP4/MOV with Rich progress bar showing frame count.
- **GPU doctor**: `vexy-stax doctor` diagnoses GPU availability with platform-specific advice (Metal/Vulkan/DirectX).
- **Compare command**: `vexy-stax compare` for image comparison with MAE, pixel match, and optional diff output.
- **FFmpeg docs**: Added installation instructions for macOS, Linux, Windows to README.
- **Test growth**: 83 → 102 tests (+7 animate, +8 GPU doctor, +4 compare).
- **Verification**: 102/102 tests passing in 1.41s.

### 2025-12-21 - Texture Filtering Fix & Visual Regression Framework
- **Texture artifacts**: Fixed horizontal banding at oblique angles by wrapping textures in `gfx.TextureMap` with `filter="linear"` for trilinear filtering.
- **Visual regression framework**: Added `image_comparison.py` with MAE/pixel match metrics, `test_visual_regression.py` comparing pygfx to JS references, and `scripts/generate_references.py` for generating JS baselines.
- **Test growth**: 68 → 81 tests (13 new for image comparison utilities).
- **Verification**: 81/83 tests passing (2 skipped pending reference image generation).

### 2025-11-06 Evening - Round 4: Package Metadata & Version Command
- **Package description**: updated pyproject.toml from "CLI tool for automating... via Playwright" to "Headless 3D renderer... (pygfx + Playwright)"; accurately reflects current architecture.
- **TODO cleanup**: marked 8 additional completed tasks across Issue 107 (Documentation) and Issue 108 (UX); two subsections now show ✅ COMPLETE status; added deferred notes for tasks requiring design/CI.
- **Version command**: added `vexy-stax version` showing package version and backend capabilities (pygfx + playwright); helps users verify installation.
- **Verification**: 68/68 tests passing in 12.26s; manual version command test successful.

### 2025-11-06 Evening - Round 3: Quality & Reliability Improvements
- **Test coverage expansion**: added 6 pytest cases for CLI validation error paths (missing file, non-JSON, invalid JSON, JSON non-object, missing 'images' field, invalid backend); 68/68 passing in 8.90s.
- **CLI help improvements**: enhanced docstrings with status badges (✅/🚧), backend trade-offs, and concrete examples; `render` command now clearly documents pygfx (fast, headless) vs playwright (pixel-perfect, requires server); class docstring explains both backends upfront.
- **Performance feedback**: added timing to both render backends; success messages now include elapsed time (e.g., "✓ PNG exported to out.png (0.42s)"); helps users compare pygfx vs playwright speed.
- **Verification**: hygiene chain clean (pyupgrade rewrote cli.py, ruff reformatted 1 file); all 68 tests pass with zero regressions.

### 2025-11-06 Evening - Pygfx Pipeline Complete & CLI Integration
- **Render pipeline**: `src/vexy_stax/render_pipeline.py` wires loader → context → scene → export for end-to-end pygfx rendering; `pygfx_render_png()` produces stills, `pygfx_render_video()` handles animations with timeline-driven frame generation.
- **Smoke test validation**: `tests/test_smoke_real_render.py` validates REAL GPU rendering (Metal on macOS); loads test scene, renders via pygfx/wgpu, exports valid PNG verified by PIL; 3/3 tests pass including scale validation and error handling.
- **CLI backend routing**: added `--backend` flag to `render` command (options: `playwright`, `pygfx`); pygfx backend requires JSON scenes and renders headlessly; Playwright backend preserved for backward compatibility (default); both backends verified working from CLI.
- **Technical fixes**: removed deprecated `wgpu.backends.rs` import; implemented proper pixel readback from offscreen canvas (`canvas.draw()` → `_last_image` → numpy); updated RenderFn signature to accept (bundle, scene, camera); fixed canvas size type conversion (float → int).
- **Test updates**: updated all renderer test mocks to match new RenderFn signature; device getter simplified to no-arg callable; 62/62 tests passing in 8.13s.
- **Verification**: Manual CLI test successful: `vexy-stax render test-img/layer123.json /tmp/test.png --backend=pygfx --width=400 --height=300` produces valid 3.7KB PNG (400×300 RGBA).
- **Quality improvements**: added upfront JSON validation (file existence, syntax, required fields) before GPU init; enhanced error messages with "Error:" + "Fix:" format providing actionable guidance; platform-specific GPU installation instructions; resource cleanup verified via try/finally blocks.
- **Documentation clarity**: added "Current Status" section to README distinguishing working features from in-progress; split installation into pygfx (recommended) vs Playwright (legacy) paths; documented both backends in render command examples with clear trade-offs.

### 2025-11-07
- **Renderer scaffolding**: added `vexy_stax.renderer` (canvas, scene_builder, textures, context) with GPU probing/offscreen bundling; pytest covers shutdown fallbacks, texture hooks, scene placement, and GPU failure handling.
- **Materials, camera, export**: `renderer.materials` maps matte/glossy/metal/glass presets, `renderer.camera` honours scene metadata and hero easing with spacing-collapse validation, and `renderer.export` ships PNG supersampling, alpha checks, and MP4 H.264/MOV ProRes fallbacks; integration tests cover colour conversion, texture wiring, opacity behaviour, and texture→scene→PNG/video flows.
- **Verification**: targeted `uvx hatch test -k` runs for materials/camera/export/pipeline complete in ≤5s; full suites hit 30/30 in 0.44s (post-scaffolding) and 50/50 in 1.41s (post-pipeline).
- **Dependencies**: added `pygfx` + `wgpu`, updating `uv.lock` (rendercanvas, pylinalg, freetype-py, uharfbuzz, ...).
- **/test cycle**: hygiene chain (`fd -e py -x uvx autoflake/pyupgrade/ruff check --fix/ruff format`) left files unchanged; `uvx hatch test` returned 53/53 in 1.76s with `/report` verification at 53/53 in 2.13s, and the post-implementation rerun now reports 59/59 in 1.86s.
- **CLI & browser reliability**: CLI image ingestion now accepts PNG/JPEG/JPG/GIF/WebP with case-insensitive sorting, uppercase `.JSON` configs load correctly, and `animate` validates timing before constructing Playwright instances; `tests/test_cli.py` gained regression coverage for these flows. `browser.export_png` now creates missing parent directories before `save_as`, with the new `tests/test_browser.py` exercising the regression.

### 2025-11-06
- **Config & docs**: introduced `src/vexy_stax/config.py` + `tests/test_config.py`, trimmed README to automation-first guidance (<200 lines), and synced PLAN/TODO/WORK with issues/101; pytest now covers 19 cases in 0.46s focused on config validation.
- **Loader & CLI coverage**: CLI tests span directory/JSON/invalid inputs and headless delegation; loader enforces PNG/JPEG/JPG/GIF/WebP allow-list, raises `LoaderError` otherwise, and `create_test_images.main` asserts PNG generation/dimensions—total CLI/loader/util cases at 11 tests.
- **Hygiene sweeps**: recurring `fd -e py -x` pipeline (`uvx autoflake`, `uvx pyupgrade --py312-plus`, `uvx ruff check --fix --unsafe-fixes`, `uvx ruff format --target-version py312`) stayed clean; `uvx hatch test` results hit 4/4 (2.51s→2.04s), 4/4 (1.98s→1.54s), 11/11 (1.57s), and 11/11 (0.58s) while manual review rechecked loader base64 handling and RGBA coercion.
- **/test & /report cycles**: hygiene chain remained no-op before 50/50 pass in 1.13s and `/report` verification in 1.02s; earlier run logged 19/19 in 0.57s with `/report` at 0.64s; pygfx draws still stubbed pending smoke-scene + CLI wiring.
- **Reliability hardening**: `vexy_stax.cli.render` now rejects invalid scales (pytest covers abort path), `export_png` creates parent directories, loader decodes via MIME-derived extensions so JPEG/WebP scenes succeed (regression test added); `/test` chain closed with 53/53 pytest cases in 1.69s.

### 2025-11-05
- **Pygfx port kickoff**: produced a nine-part execution plan in `external/plan/` (architecture, ingestion, rendering, animation, export, QA); implemented schema-driven loader (`models.py`, `loader.py`) converting vexy-stax JSON into RGBA numpy textures with robust error handling; replaced legacy validation tests with loader-focused coverage and lazy Playwright imports for test isolation.

### 2025-11-04
- **Maintenance audit**: `create_test_images.py` now catches `OSError` when Helvetica is missing, falling back to the PIL default font and removing the bare `except`, keeping Ruff compliant.

### Legacy Quality Rounds (R10 → R3)
- **Round 10**: memory guard rails compute 4B/pixel, warn at 500 MB, demand confirmation at 1 GB, mirror status in the FPS panel, and throttle prompts for 30 s; file-type validation accepts PNG/JPEG/JPG/GIF/WebP/SVG, rejects others with toasts, filters invalid drag/drop and input entries, and logs accepted vs rejected counts; keyboard navigation adds tab-focusable lists, arrow traversal, Enter highlight, Delete/Backspace removal with confirmation, persistent outline, and ARIA hints.
- **Round 9**: FPS counter toggles via `window.vexyStax.showFPS`, colour-codes thresholds, keeps a rolling average, and warns via console while remaining accessible through `getStats` with no idle overhead; undo/redo tracks 10 states with Ctrl/Cmd+Z and Shift+Z across add/delete/clear flows, updates the help overlay, and surfaces toast feedback; export confirmation wraps PNG writes in try/except, toasting successes with file size and failures with reasons plus verbose console diagnostics; the reusable `showToast` helper now supports typed styles, auto-dismiss timers, slide animations, and bottom-right staging.
- **Round 8**: window resize debounce (150 ms) cancels stale callbacks and cuts resize thrash by ~90%; image loads retry exponentially (0.5/1.5/3.0 s) with logged attempts and error clears; WebGL context loss/resume is handled by rehydrating textures and broadcasting recovering/recovered banners.
- **Round 7**: localStorage recovery detects `QuotaExceededError`, prompts for clearance, retries automatically, and degrades gracefully when storage is unavailable; the debug console API exposes `window.vexyStax` helpers (export, clear, settings, stats, help) with a highlighted init banner; a `beforeunload` disposer releases geometries, textures, controls, and the WebGL context inside try/catch.
- **Round 6**: keyboard shortcuts add Ctrl/Cmd+E export, Ctrl/Cmd+Delete clear with confirmation, `?` help overlay toggle, and Esc dismiss; settings persist/load via localStorage with reset button and fallbacks; export progress overlay blocks 2×–4× renders with scale messaging and skips 1× outputs.
- **vexy-stax-wl planning phase**: authored a 25 KB (500+ lines) plan in PLAN.md, 70+ TODO items, dependency justifications (DEPENDENCIES.md, 10 KB), and supporting WORK/CHANGELOG/README artefacts, noting the critical finding that Leva is React-only and demands an architectural rewrite.
- **Round 5**: capability detection consolidates WebGL/FileReader/Canvas checks, gating unsupported browsers with a modal; image validation warns at 10 MB, rejects at 50 MB or >4096 px with guided confirmations and friendly errors; visual regression guardrail adds baseline PNGs plus PIL diff (≤1% / ±10 RGB) to `test.sh`, increasing suite size from 7 to 8.
- **Round 4**: documentation refresh introduced project-level README, vexy-stax-wt vs vexy-stax-wl comparison tables, a variant decision guide, and a comprehensive `vexy-stax-wl/README.md` covering planning status.
- **Round 3**: `test.sh` hang removed by pruning dead directories, streamlining the script, layering visual regression, and holding runtime under one second, with Tweakpane UI and pm renderer verified alongside capability checks (8/8 green on 2024-11-04).

## [Unreleased] - 2024-11-04 Session 1

### Added - New Projection Modes
- `vertical_stack`: map Z→Y (u=x, v=-(z+0.3y)) so layers climb vertically in both pc and pm variants.
- `horizontal_stack`: map Z→X (u=z+0.3x, v=y) so layers slide sideways in pc and pm builds.

### Added - Quality Improvements Round 2
- Path resolution: run.py executes relative to config directory, creating outputs automatically.
- Example configurations: 11 documented JSON examples (4 pc, 7 pm) covering projection presets.
- Test automation: root `test.sh` orchestrates four suites with PIL PNG validation, backups, colourised output, and timeouts.

### Added - Quality Improvements Round 1
- Config standardisation: nested `output` blocks unify structure across projects.
- Config validation: `validate_config()` enforces schema, required fields, and file existence with clear errors.
- Output validation: `validate_output.py` checks PNG format, dimensions, integrity, and metadata.

### Added - Test Infrastructure
- Test layers: 400×300 red/cyan/yellow PNGs in `test-img/` for instant visual checks.
- Validation tool reuse: same `validate_output.py` powers automated PNG inspections across projects.

### Testing
- All pc/pm/wl/wt variants verified (800×600 outputs, RGB/RGBA as expected).
- Projection presets (vertical/horizontal stack) exercised in both engines.
- Example configurations and path resolution workflows executed successfully.

### Changed
- Updated pc/pm `run.py` files to resolve paths via `config_path.parent` and extend projection/viewpoint registries.

### Technical Details
- Projection maths: 0.3 coefficient for depth cues with Z mapped to screen axes per mode.
- Path handling: `pathlib.Path.resolve()` ensures cross-platform absolute paths while keeping JSON-relative semantics.
- Example JSONs: self-contained definitions referencing test layers with documented usage guidance.
