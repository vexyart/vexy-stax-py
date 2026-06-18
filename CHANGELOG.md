<!-- this_file: CHANGELOG.md -->

# Changelog

All notable changes to this project are documented here.

## [3.0.12] — issue 337

### Fixed

- **Compact view reserved empty caption space** (337): after issue 332 moved the captions between
  the floor and the slide plates, `compact_camera` framed the slide+caption COMPOSITE (height
  `H + lift`, aimed at `Y = lift/2`) — but captions are invisible in the compact view (they fade
  in only as the deck expands), so the reserved caption-plate height padded the frame at the bottom
  and (via the aspect fit) the sides. `compact_camera` now fits ONLY the frontmost SLIDE plate
  (height `H`, aimed at the slide center `Y = lift`), so the slide fills the frame tight with no
  caption gap. The expanded view still frames the full composite (where the captions ARE visible).
  Verified: pygfx + playwright + blender compact stills fill the frame edge-to-edge with no padding;
  geometry tests updated. Mirrored in `vexy-stax-js` (`compactCamera`).

## [3.0.11] — issue 335

### Added

- **`video` scene section** centralizing the video render params (`vexy_stax.scene.Video`,
  schema `#/properties/video`): `width`/`height` (default to `scene.size`), `fps` (default
  ⇒ `transition.fps`, else 30), `frames` (transition frames per leg; default
  ⇒ `round(duration × fps)`), and `first_hold`/`last_hold` (held still-frame counts, default
  10 each). The `transition` block still owns the animation (`kind`/`easing`/`wait`/`duration`);
  `video` owns the output framing. All engines read these for video via the new
  `geometry.video_fps` / `geometry.video_dimensions` / `geometry.transition_frames` helpers.
- **Held first/last still frames in transition videos (default-on).** `geometry.frame_plan`
  now prepends `first_hold` copies of the first frame and appends `last_hold` copies of the
  last (`still(N) → transition → still(N)`), so every clip opens and closes on a steady image.
  Override per call: `frame_plan(scene, first_hold=…, last_hold=…)` or
  `stax video --first_hold … --last_hold …`.
- **`vexy_stax.showcase` module** holding the showcase/benchmark logic (per-engine render loop,
  std>20 near-blank gate, linear-easing showcase transition, benchmark file, JS-demo rebuild)
  behind a clean `run_showcase(...)` API. `example.py` is now a thin wrapper.
- **CLI overrides** on `stax video`: `--width --height --fps --frames --first_hold --last_hold`.

### Changed

- `example.py` reduced to a thin wrapper around `vexy_stax.showcase.run_showcase` (behavior
  unchanged: same outputs, same std gate, same linear showcase transition, same JS-demo rebuild).
- The playwright engine strips the `video` section from the config handed to vexy-stax-js
  (consumed Python-side; the JS parser rejects unknown keys until JS mirrors the field).

## [3.0.10] — issue 334

### Fixed

- **pygfx `transition.mp4` corrupted ~40 % in after playback in QuickTime/QuickLook** (334): the
  pygfx and playwright mp4s share the exact same ffmpeg encode, yet only pygfx's corrupted in macOS
  VideoToolbox (ffmpeg's software decoder, and playwright/blender's smoother frames, were unaffected).
  Root cause: B-frames + a single IDR keyframe — VideoToolbox desynced on pygfx's hard aliased edges
  and, with no later keyframe, never recovered. The shared `_encode_video` (pygfx + playwright) now
  encodes `-bf 0` (no B-frames), a keyframe every `fps` frames (`-g`/`-keyint_min`, so any desync
  self-heals within ~1 s), `-profile:v high`, and explicit bt709 / limited-range color tags so
  VideoToolbox interprets the stream correctly. Verified: `has_b_frames=0`, periodic keyframes,
  `color_range=tv`, and a clean macOS QuickLook (VideoToolbox) decode of the regenerated 4K clip.

## [3.0.9] — issue 332

### Added

- **Global `captions` on/off toggle** (332): a new top-level boolean scene field (default `true`,
  preserving prior behavior) parsed + validated in `scene.py` and `schema/vexy-stax-scene.schema.json`.
  When `false`, no caption plates are drawn (every engine + the geometry's `caption_opacities` skip
  them) and the slide plates drop directly onto the floor.

### Changed

- **New stacked caption layout** (332): when captions are ON, each caption plate sits RIGHT ON the
  floor (bottom edge on the floor line) and its slide plate sits directly ON TOP of it (slide bottom
  edge == caption top edge), LEFT-aligned with the slide (caption left edge == slide left edge at
  `X = -width/2`). This replaces the previous "caption to the LEFT of the plate" layout.
  - `geometry.py`: added `slide_lift(scene)` (one caption-plate height when captions on, else 0);
    every slide plate is lifted by it. `caption_anchor_x` now means the caption plate's LEFT edge
    (numerically unchanged since `CAPTION_GAP_EM == 0`). `caption_opacities` returns all-zero when
    `captions` is off.
  - **Crop-free camera framing for the full composite**: `compact_camera` now fits the frontmost
    COMPOSITE (width `W`, height `H + lift`) and aims at its center (`Y = lift/2`); `expanded_camera`
    includes the lifted slide corners AND the on-floor caption-plate bottom row in its bounding fit,
    so the caption+slide stack is framed with no crop in either view.
  - Engines (`engines/pygfx.py`, `engines/_blender_render.py` + `engines/blender.py`) honor the
    toggle, lift slides/borders/reflections, and anchor caption plates by their LEFT edge on the
    floor. The `playwright` engine inherits the layout from the shared JS geometry/stage.

## [3.0.8] — issues 325, 328, 329, 330

### Fixed

- **Transition video "froze" after ~1 s** (329): the showcase clip used `easeInOutCubic`, which
  — combined with the expanded camera receding very far — placed only ~2 % of the camera motion in
  the final 0.33 s, so the deck appeared to stop moving half-way through. `example.py` now renders
  the showcase transition with `linear` easing (~17 % of the motion in every 0.33 s bucket), so the
  clip animates continuously to the end. Verified: 0 near-static tail frames (was the whole last
  third).
- **pygfx / playwright `transition.mp4` encoding hardened** (329): both `_encode_video` helpers now
  pass `-crf 18` and `-movflags +faststart`, matching the Blender reference encoder (was libx264 /
  yuv420p with default CRF and no faststart). The output stays valid H.264 / yuv420p with even
  dimensions.
- **`expanded.png` flagged as a false failure** (329): the showcase gate required `std > 28`, but the
  expanded view is an intentionally sparse layer-explosion whose legitimate 4K std is ~23–24 across
  all three engines (a blank/broken render is < 10). The gate is now `std > 20`, a near-blank guard
  that no longer fails the correct sparse framing. (Per design decision: keep the spread look; the
  `camera.gap` is honored — `test_expanded_camera_margins_match_gap` confirms margin == projected
  gap.)
- **Bundled-font glob leaked workspace cruft** (328): `tool.hatch.build.targets.wheel.artifacts`
  was `fonts/*`, which swept a stray `.omc/` session file into the wheel. Narrowed to
  `fonts/*.ttf` + `fonts/*.txt`; the `vexy-stax.ttf` face (+ `OFL.txt`) still ships, the cruft no
  longer does.
- **Stale unit tests after the deck shrank to 8 slides** (325): `test_scene`/`test_geometry` still
  assumed the old 9-slide deck (the dropped `010-back` layer) and camera elevation 0, so 6 tests
  failed independently of any render. Updated the slide count (9→8), back-most slide
  (`010-back`→`020-source`), halftone index (7→6) and the expanded-camera elevation expectation to
  match the authored testdata. Suite is green.

### Verified (no code change needed)

- **Blender compact-view black middle + transition translucency** (325): confirmed already fixed by
  the 3.0.7 `transparent_max_bounces` work — the committed `outputs/blender/*` were simply stale.
  Fresh full-res renders show compact std ≈ 99.7 (pink backdrop visible through the transparent
  lettering layers) and clean, non-translucent mid-transition plates.
- **Blender render speed** (325): the 3.0.7 speedups hold — a full-res (3840×2482) compact still now
  renders in ~43 s (was ~400 s+).

### Changed

- **`example.py` rebuilds the sibling JS demos** (330): after the Python renders it best-effort runs
  `vexy-stax-js/example.sh`, regenerating `vexy-stax-js/outputs/{scrollable,playable}.html` (and
  cleaning stale `outputs/` via that script's `rm -rf`). Skipped — never fatal — when bash/node or
  the JS package is unavailable.

## [3.0.7] — issues 325, 328

### Changed

- **Default caption font → bundled `vexy-stax.ttf`** (328): the default caption font is now the
  bundled `src/vexy_stax/fonts/vexy-stax.ttf` (Zalando Sans Expanded, with tracking baked in)
  instead of REM. `geometry.default_font_path()` points at it; the pygfx engine registers it with
  the font manager and maps the default-font aliases ("Zalando Sans"/"vexy-stax"/…) and an unset
  font to it; the blender engine loads it for any non-path font. Showcase testdata drops the
  explicit `font` so captions use the default. (JS uses the matching Google Font — see vexy-stax-js.)
- **Blender render speedups** (325): samples 24→16 (turbo 16→8); shallow light bounces
  (`max_bounces` 8→4, diffuse/glossy 3→2, transmission 8→4) since the plates are flat and
  unlit; aggressive adaptive sampling (`adaptive_threshold` 0.01→0.02, `adaptive_min_samples` 4);
  reflection blur now runs on a ≤1024px-tall downscaled copy (~16× cheaper, visually identical
  under the glass); and the transition VIDEO long-edge is capped at 1920 (a motion preview — the
  stills keep full resolution), so a 4K showcase video no longer takes ~1 h.

### Fixed

- **Blender compact view rendered black** (325): the committed `outputs/blender/*` were stale
  (rendered before the 327 `transparent_max_bounces` fix). Regenerated — the compact view now
  shows the pink backdrop through the transparent lettering layers, and the transition no longer
  goes translucent near the compact end (same root cause: the dense head-on transparent stack).

## [3.0.6] — issue 327

### Fixed

- **pygfx captions rendered with a heavier fallback font** (327.2): the bundled
  `REM-Regular.ttf` is now registered with pygfx's font manager (`add_font_file`)
  and captions pass the resolved family NAME, so they render REM-Regular instead of
  pygfx's built-in fallback (which read artificially bold). New `_register_font` /
  `_caption_font_family` helpers.
- **pygfx caption plates bled through each other** (327.3): caption pieces shared a
  single GLOBAL render order, so every caption's text painted over every caption's
  fill and neighbouring captions overlapped translucently. Each caption now gets a
  contiguous render-order block that increases with the slide index (front plates =
  higher index = painted last), so a front caption's opaque fill fully occludes the
  captions behind it.
- **playwright caption borders** (327.4): resolved by 326 (borders off by default).
  The playwright caption font fix lives in the `vexy-stax-js` package ([3.0.6]).

## [3.0.5] — issue 326

### Changed

- **Plate + caption borders OFF by default** (326): `Edge.width` default `0.004 → 0.0`.
  A border (around both the slide plates and the caption plates, which share
  `edge.width`) now draws only when `width > 0`. `testdata/airbl.scene.json` sets
  `"edge": {"width": 0}` explicitly. Border color defaults are unchanged and apply
  only when a border is enabled.

## [3.0.4] — issues 324–325

### Changed

- **Caption + border colors default `#f2f2f2`, each overridable** (324): the
  default slide-plate border, caption-plate fill and caption-plate border are now
  `#f2f2f2` (was `#cccccc`). Each is independently overridable in scene JSON:
  `scene.edge.color` (slide border), `caption_defaults.fill_color` (caption fill),
  `caption_defaults.border_color` (caption border) and `caption_defaults.color`
  (caption text). New `geometry.caption_fill_color()` / `caption_border_color()`
  helpers (each falling back to `scene.edge.color`); the pygfx and blender engines
  resolve the caption plate fill/border through them. Schema + `CaptionStyle`
  gained `fill_color` / `border_color`.
- **Caption font 1/3 larger by default** (324): `CAPTION_PLATE_HEIGHT_FRAC`
  `0.10 → 0.10·4/3 ≈ 0.1333`, so `CAPTION_DEFAULT_SIZE_FRAC` `0.075 → 0.10` of the
  scene height. Showcase testdata caption sizes bumped to match (403 / 81).

### Fixed

- **Blender compact view rendered black; transition went translucent** (325):
  in the compact view every plate stacks head-on, so a single camera ray crosses
  all of them. Each plate is a 2-faced `SOLIDIFY` slab (plus a mirrored
  reflection), so a center ray crosses ~`4·N` transparent surfaces before reaching
  the opaque backdrop. The `transparent_max_bounces` budget — lowered to
  `max(16, n·2)` for speed in 320.8 — was exhausted by the dense stack, and an
  exhausted transparent ray makes Cycles return **black** (the "black where it
  should be pink" report, and the translucent frames near the compact end of the
  transition). Raised to `max(64, n_plates·4)`; transparent bounces are cheap
  pass-throughs, so render time is essentially unchanged. Verified: compact still
  now shows the pink backdrop through the transparent lettering layers.

## [3.0.3] — issues 321–323

### Changed

- **Caption plate touches slide plate** (321/323): `CAPTION_GAP_EM` reduced from
  `2.0` to `0.0` in `geometry.py` so the caption plate right edge aligns exactly
  with the slide plate left edge — no visual gap.
- **Caption plate fill = border color** (323): already implemented in 320 (pygfx
  engine uses `edge_rgb` for the fill quad).
- **Testdata typography explicit** (322): `airbl.scene.json` already carries
  `"font": "REM"` and `"size": 302` in `caption_defaults` (added in 320).

## [3.0.2] — issue 320

### Added

- **Bundled REM font** (320.1): `REM-Regular.ttf` is now shipped inside the
  Python wheel under `src/vexy_stax/fonts/` (via `pyproject.toml` artifacts).
  `geometry.default_font_path()` returns its path when present.
- **REM as default caption font** (320.2): `pygfx` engine uses the bundled
  `REM-Regular.ttf` when no explicit font is set in the scene or style.

### Changed

- **Caption plate fill = border color** (320.7): caption plate fill color is now
  the same as the slide-plate border/edge color (`scene.edge.color`, default
  `#cccccc`) instead of white, matching the JS renderer.
- **Blender render speed** (320.8): default Cycles samples reduced from 512 → 64
  (with OPENIMAGEDENOISE still active), cutting render time by ~8×.
- **Testdata uses REM font** (320.4): `airbl.scene.json` and
  `airbl-lores.scene.json` now specify `"font": "REM"` in `caption_defaults`.

## [3.0.1] — issues 303–318

### Fixed (issue 318)

- **`install.sh` system Python install** (318): `vexy-stax-py/install.sh` now
  additionally runs `uv pip install --system -e .` after `uv sync`, so that
  `example.py` (and any other script using `#!/usr/bin/env python3`) can be
  invoked directly from the repo root without activating the `.venv` first. The
  system install step is soft-fail — if `--system` access is denied it prints a
  warning and continues.
- **`pyproject.toml` fallback-version** (318): bumped `fallback-version` to
  `3.0.1` to match the JS package version.

### Added (issues 316, 317)

- **Caption font family + size entries** (316): `caption_defaults` in the testdata
  now carries explicit `size` + `font` (documented in the schema's `captionStyle`),
  and both engines resolve them (`caption_size` reads `.size`; Blender/pygfx/JS apply
  `.font`). The default (no explicit `size`) remains 7.5% of plate height (315).
- **`example.py`** (317.1): the showcase runner is now Python (replacing `example.sh`),
  rendering pygfx **first** and Blender **last** (317.2).
- **High-quality Blender rendering** (317.3): the showcase renders Blender in **Cycles**
  (no `VEXY_STAX_TURBO`), which fixes the bottom-of-frame **white wash + flicker** seen
  with Eevee — that artifact was Eevee's unstable transparency sorting drawing the
  semi-transparent floor over the plate; Cycles ray-traces transparency correctly. Higher
  quality, slower (tests still use Eevee/turbo for speed).

### Removed

- **Floor shadows** (312): the short pale plate shadows on the floor (added under
  307) were eliminated in every engine, along with the `SHADOW_*` geometry constants.

### Added

- **Smoked-glass reflective floor** (303 §1): `Floor` defaults to a "just so
  visible" dark smoked glass (`color=#1a1a1a`, `opacity=0.04`); the plate
  reflections are now **blurred** (soft, not a crisp mirror) in all engines via a
  shared `REFLECTION_BLUR_FRAC` (Gaussian/box blur of the reflection texture). pygfx
  blurs a downscaled copy (GPU upsamples it) so large plates stay fast (~2.5s).
- **Compact "fit tight"** (303 §2): default `camera.distance` is now `"100%"`
  (the limiting axis fills the frame, no unneeded padding; aspect-ratio padding
  only when the viewport aspect differs from the plate).
- **Plate edge / border** (305): new `Edge` scene model (`width` as a fraction of
  plate height, default `0.004` thin; `color` default `#cccccc`), **on by default**.
  Drawn as 4 thin perimeter quads per plate (works through plate transparency) in
  every engine, via the shared `plate_edge_width(scene)` helper.
- **Caption plates** (311, typography revised by 315): captions render as small
  **white opaque bordered plates** (same edge as the slide plates) instead of floating
  text. Plate height = **10%** of the frontmost plate height; text 1em = 75% of the
  caption-plate height (→ 7.5% of plate height — supersedes 308's 5%); plate width =
  text + **0.75em** padding each side. Shared geometry: `caption_plate_height`,
  `caption_plate_center_y`, `CAPTION_PLATE_HEIGHT_FRAC`/`CAPTION_FONT_FRAC_OF_PLATE`/`CAPTION_PLATE_PAD_EM`.
- **Frame-based caption stagger** (309): `CaptionFade.stagger_frames` lets the
  back→front per-caption fade step be set in transition *frames* (overrides the
  `stagger` fraction); `caption_opacities` converts it via the per-leg frame count.
- **Ease-in-out video movement**: the showcase transition is explicitly
  `easeInOutCubic`.

### Fixed

- **Playwright stale-bundle crash** (310): the `dist` bundle is rebuilt so the JS
  scene parser accepts the new `edge` key (was: "Unknown key 'edge' in scene").
- **playable.html scale at HiDPI** (304.1): `stage.js` now uses
  `renderer.setSize(w, h)` (updateStyle=true) so the canvas displays at its CSS
  size, not the 2× device-pixel backing size.

## [Unreleased] — issue 302

### Added

- **Dual-axis crop-free compact framing** (G002): `compact_camera` now uses
  `d_fit = max(d_w, d_h)` so the limiting axis touches exactly `P%` of the frame
  and the other axis never crops, regardless of viewport/scene aspect mismatch.
  Implemented identically in `geometry.py` and `geometry.js`.
- **Margin-matched expanded framing** (G003): `expanded_camera` solves camera
  distance + horizontal re-centering pan by bisection so that the projected left
  and right viewport margins each equal the projected inter-plate gap. Implemented
  identically in `geometry.py` and `geometry.js`.
- **Caption model** (G004): `CaptionFade` dataclass (`window`, `stagger`);
  `caption_anchor_x(scene)` helper; `caption_opacities(scene, t)` staggered
  back→front fade function; `FrameState.caption_opacities` field carrying
  per-frame opacities into every engine. All in `geometry.py` + `geometry.js`.
- **Caption render — all engines** (G005):
  - `blender/_blender_render.py`: captions at `(anchor_x, 0, z)`, `align_x=RIGHT`,
    opacity from `frame_job["caption_opacities"]`.
  - `engines/pygfx.py`: captions at `(anchor_x, 0, z)`, `anchor="middle-right"`,
    opacity from `state.caption_opacities`.
  - `vexy-stax-js/src/stage.js`: captions as THREE.Sprite with
    `ctx.textAlign="right"`, `sprite.center=(1,0.5)`, positioned at
    `(captionAnchorX, 0, plateZ)`, opacity from `captionOpacities(scene,t)` or
    `state.captionOpacities`.
  - `engines/playwright.py`: `_frame_state_dict` renames `caption_opacities` →
    `captionOpacities` so JS `applyFrameState` receives the correct camelCase key.
- **Smooth video defaults** (G006): `example.sh` transition override now uses
  30 fps / 2 s / wait 0 = 60 frames (single expand leg).
- **JS unit tests for caption layout** (`vexy-stax-js/tests/stage.test.js`): 5
  tests using Node 26 `registerHooks()` THREE stub covering center anchor,
  `textAlign`, position, opacity, and visibility threshold.
- **Python tests** (`tests/test_geometry.py`): `test_frame_state_dict_caption_key_camelcase`
  and `test_caption_opacities_aligned_with_slides` (ungated, run in all environments).
- **Caption fade in the scene format**: optional top-level `caption_fade` `{window,
  stagger}` (pydantic `CaptionFade`, `scene.js` parser, and
  `schema/vexy-stax-scene.schema.json`).
- **Responsive playable demo** (G008): `verify/example.mjs` generates a polished
  `outputs/playable.html` — the stage is locked to the scene's aspect ratio and
  capped by viewport height (no canvas distortion at any size), vertically centered
  on a gradient, auto-plays the expand on load, and highlights the active view.
- **Cross-engine verification harness** (`verify_302.py`): extracts the first/last
  video frame of each engine and reports a cross-engine SSIM parity matrix.

### Changed (caption placement — em-based, per the reference spec)

- Captions are now anchored by an **em metric** (1em = `geometry.caption_size`):
  the text-block **right edge** sits `2em` left of the plate left edge
  (`caption_anchor_x`) and the text **baseline** sits `1em` above the virtual ground
  (`caption_baseline_y`, the floor at the bottom of the plates) — replacing the earlier
  "centered at Y=0, 0.04·width gap" placement. Engines anchor right + baseline (Blender
  `align_y=BOTTOM_BASELINE`, pygfx `anchor="baseline-right"`, JS sprite baseline anchor),
  and all engines size captions from the shared nominal `caption_size` so 1em == size
  world units consistently. New shared helpers `caption_size` + `caption_baseline_y`
  (py + js, numerically identical); JS drops the `texScale` caption hack.

### Fixed

- **pygfx camera framing parity** (G007): pygfx's `PerspectiveCamera.fov` is a
  width+height *mean* (`size = 2·near·tan(fov/2)`, `height = 2·size/(1+aspect)`), not a
  vertical fov like three.js/Blender, so feeding it the three.js vertical fov rendered
  the deck ~`(1+aspect)/2` too zoomed (compact cross-engine SSIM was 0.32). New
  `_pygfx_fov_deg()` inverts pygfx's formula at both camera sites; compact/expanded/
  video parity is now ≥0.96 across blender, pygfx, and playwright.
- **pygfx caption size**: dropped an erroneous extra `* self._scale` that shrank
  captions to near-invisibility; `gfx.Text` font_size is already in plate world units.

### Changed

- `vexy-stax-js/tests/stage.test.js` stubs `three` via `node:module` `registerHooks`
  (stable on Node ≥22.15) and **skips** on older runtimes, so the published package's
  `engines.node` stays `>=18.0.0` (the library's real requirement) rather than being
  raised to satisfy a dev-only test.
- `SPEC.md`: §6.5 documents caption sprite implementation; §8 references G007
  (VerifyIterate) instead of G010; `stage.js` and `transition.js` added to JS
  test list; §4 symlink note corrected to "real copy"; §10 converted to §9
  "Completed implementation phases" in past tense.
- `TODO.md`: title updated to cover issues 301 + 302; Phase 11 (issue 302
  completed work) and Phase 12 (pending G007/G008) added.

## [3.0.0]

### Added

- Self-contained release of `vexy-stax-py` as the canonical home for the shared
  scene format (github.com/vexyart/vexy-stax-py, PyPI):
  - `schema/vexy-stax-scene.schema.json` + `schema/examples/airbl.scene.json` —
    the canonical scene schema and example are now bundled in-repo. The example
    `src` paths resolve to the repo's own `testdata/airbl-lores/` slides, so the
    package and tests have zero parent-directory dependencies.
  - `SPEC.md` — the binding scene-format specification, bundled at the repo root.
  - `tests/test_juicy.py`, `tests/test_images.py`, `tests/conftest.py` — unit
    tests for `juicy.py`/`images.py` configured for the repo-local `airbl-lores`
    fixtures (8 layers, 1246x806).

### Changed

- `pyproject.toml` — `[tool.hatch.version] fallback-version = "3.0.0"`; added
  `[project.urls]` Homepage/Repository.
- `.github/workflows/ci.yml` — added a `ruff check src tests` lint step.
- `.github/workflows/release.yml` — scoped `id-token`/`contents` permissions to
  the jobs that need them (PyPI Trusted Publishing, GitHub Release).
- `.gitignore` — ignore rendered `outputs/`.

## [Unreleased]

### Added

- Initial scaffold for `vexy-stax-py` (issue 301 §2 / SPEC.md phase 2):
  - `pyproject.toml` — hatchling + hatch-vcs build, project `vexy-stax`,
    Python ≥3.12, deps `fire`/`rich`/`pillow`/`numpy`/`pydantic>=2`/
    `opencv-python-headless`, `vexy-stax` console script.
  - `scene.py` — pydantic v2 models for shared scene format v1, matching
    `schema/vexy-stax-scene.schema.json` exactly; `extra="forbid"` on every
    model; scalar/per-view opacity; `load_scene()` with path resolution.
  - `geometry.py` — pure, engine-agnostic view geometry (SPEC.md §3): gaps,
    stack depth, compact/expanded camera poses, easing curves, opacity
    interpolation, and a total `frame_plan()` per transition.
  - `engines/` — `Engine` protocol, lazy availability-probing registry, and
    the three render engines: `blender`, `pygfx`, and `playwright`.
  - `images.py`, `juicy.py` — overlay compositing and color-correction modules.
  - `cli.py` — fire + rich CLI: `render`, `video`, `overlay`, `engines`.
  - `tests/` — scene and geometry unit tests with shared fixture vectors.
