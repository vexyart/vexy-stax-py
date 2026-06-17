<!-- this_file: SPEC.md -->

# Vexy Stax — Specification

Render a deck of layered PNG "slides" as 3D glass plates, in two views and the
transitions between them, from a single shared JSON scene format. Two
deliverables share that format:

- **vexy-stax-py** — offline Python package (PyPI), renders stills and video
  via three interchangeable engines (Blender, pygfx, Playwright).
- **vexy-stax-js** — browser JS package (npm), renders stills, video, a playable
  animation, and a scroll-driven ("scrollspy") transition; ships as a Web
  Component, an ESM module, and a classic-script global.

This document is the contract and unified specification for the scene format and render engines.

---

## 1. Concepts and terminology

A **scene** is an ordered list of **slides** (layered images) plus view and
render settings. Slides are ordered back-to-front: index `0` is farthest from
the camera, the last index is closest. With `testdata/airbl-lores/`,
`airbl-020-source.png` is index 0 (farthest) and `airbl-090-ui.png` is last
(closest).

Each slide is a flat upright plate standing on a floor at `Z=0`, bottom-aligned
to the tallest slide, horizontally centered, with the vertical middle of the
tallest slide at `Y=0` (per legacy `SCENE.md §1`).

Two **views** only (issue 301 §4):

| This spec   | Legacy aliases                  | Description                                              |
|-------------|---------------------------------|----------------------------------------------------------|
| `expanded`  | beauty, angled, hero-shot start | Angled camera; plates spaced apart by `gap`; captions on |
| `compact`   | stack, hero, straight-on        | Head-on camera; plates collapsed to `MIN_GAP` (≈3 pt)    |

A **transition** animates between the two views over `duration` seconds, with an
optional `wait` hold at the far end:

| Transition          | From → To (→ hold → back)        |
|---------------------|----------------------------------|
| `expand`            | compact → expanded               |
| `collapse`          | expanded → compact               |
| `expand_collapse`   | compact → expanded → compact     |
| `collapse_expand`   | expanded → compact → expanded    |

During any transition, per-slide **opacity** is interpolated alongside camera
and spacing (the one addition issue 301 §3 mandates over the legacy format).

---

## 2. Shared scene format v1

One JSON document, consumed identically by both packages. Pydantic model in
Python (`vexy_stax.scene`), Zod/plain-object parser in JS (`scene.js`). Schema
published as `schema/vexy-stax-scene.schema.json` and referenced by `$schema`.

```jsonc
{
  "version": 1,
  "view": "expanded",                  // initial view: "expanded" | "compact"
  "size": { "width": 1920, "height": 1080 },
  "camera": {
    "gap": 1920,                        // pt between adjacent plates (expanded)
    "distance": "90%",                  // absolute pt ("500") or viewport-fit ("90%")
    "angle": 60,                        // azimuth degrees (expanded)
    "elevation": 0,                     // degrees above horizon (expanded)
    "fov": 39.6                         // perspective FOV (≈50mm); optional
  },
  "transition": {                       // optional; omitted ⇒ still render
    "kind": "expand_collapse",          // expand|collapse|expand_collapse|collapse_expand
    "duration": 3.0,                    // seconds per leg
    "wait": 1.0,                        // hold seconds at the far end
    "fps": 30,
    "easing": "easeInOutCubic"          // shared easing name (see §2.3)
  },
  "floor": {                            // smoked glass, blurry reflections (issue 303 §1)
    "color": "#1a1a1a",                 // smoked tint (dark; barely visible on light bg)
    "opacity": 0.04,                    // ~4% — "just so visible"
    "reflectivity": 0.5                 // blurred mirror-reflection strength
  },
  "edge": {                             // visible plate border, default-on (issue 305)
    "width": 0.004,                     // thickness as a fraction of plate height (thin)
    "color": "#cccccc"                  // light gray
  },
  "background": "#ffffff",
  "juicy": false,                       // py only: per-channel color match (see §5.4)
  "caption_defaults": { "size": null, "color": "#222222", "font": null },  // size null ⇒ 10% of plate height (issues 311/315/324); font null ⇒ bundled vexy-stax.ttf / "Zalando Sans" (issue 328)
  "caption_fade": {                     // optional; caption fade-in timing (see §2.2)
    "window": 0.9,                      // captions fade in over the final 90% of the morph
    "stagger": 0.3,                     // back→front succession spread (fraction of window)
    "stagger_frames": null              // issue 309: per-caption step in FRAMES (overrides stagger)
  },
  "slides": [
    {
      "src": "airbl-020-source.png",    // path rel. to scene file; or "data:" base64
      "gap": null,                      // per-slide gap override (null ⇒ camera.gap)
      "opacity": { "expanded": 1.0, "compact": 1.0 },   // morphable; see §2.1
      "caption": { "text": "Source", "show_in": "expanded" }  // see §2.2
    }
  ]
}
```

### 2.1 Morphable opacity (the new feature)

`slide.opacity` is the one extension over the legacy format. It MUST accept
either form:

- **scalar** `0.9` — constant opacity in both views.
- **per-view** `{ "expanded": 1.0, "compact": 0.4 }` — opacity is keyed to each
  view and **interpolated during transitions** using the transition easing, in
  lockstep with the camera/spacing morph. At view endpoints opacity equals the
  endpoint value exactly.

Opacity multiplies the slide's image alpha (premultiplied). `0` ⇒ fully
invisible (subsumes the legacy per-plate `hide` flag: `hide` ≡
`{ "compact": 0 }`). Engines MUST clamp to `[0, 1]`.

Rationale: a slide can fade in only when the deck expands (storytelling), or fade
out as it collapses, independently of geometry. Keeping it per-view (not arbitrary
keyframes) keeps the format small and matches the two-view scope of issue 301 §4.

### 2.2 Captions (issue 301 §5, typography issue 302 §B)

`slide.caption` places a text label to the **left** of its plate. `show_in` is
`"expanded"` (default), `"compact"`, `"both"`, or `"none"`.

**Caption plates (issues 311, 315).** Each caption is a small **white opaque plate** with
the same border as the slide plates (`scene.edge`), with the text centered on it — not
floating text. Let `1em` = the nominal caption size (`geometry.caption_size` =
`caption_defaults.size`, else `0.075·height`). The caption-plate height is `caption_size / 0.75`
(so the text 1em is 75% of the plate height; the default plate height is `0.10·height` —
issue 315 revised this from 311's 20%). The plate width is the typeset text width + `0.75em`
padding on each side (issue 315, was 1.5em). The plate's **right edge**
lands `2em` left of the plate left edge, `X = -(scene.size.width/2 + 2·em)`
(`geometry.caption_anchor_x`); its **vertical center** is `geometry.caption_plate_center_y`
(the plate sits on the virtual ground). Each caption keeps its plate's `Z`, so in the angled
expanded view the caption plates recede alongside the deck. (Floor shadows were removed —
issue 312.)

**Fade (full opacity only in expanded).** Caption opacity is a function of the morph
factor `t` (0=compact, 1=expanded), computed once in `geometry.caption_opacities` and
consumed by every engine (and carried per-frame on `FrameState.caption_opacities`), so
all renderers fade identically:
- `expanded` captions are invisible in compact and fade in only during the **final
  `window` fraction** of the morph (`caption_fade.window`, default `0.9`), **staggered
  back→front** (`caption_fade.stagger`, default `0.3`) so the backmost label leads and
  the frontmost reaches full opacity exactly at `t = 1` — captions are at full opacity
  *only* in the expanded view.
- `compact` fades out symmetrically as the deck expands; `both` is always on; `none`
  is always off.

**Styling.** Optional `caption.style` (`{ size, color, font }`) is engine-best-effort,
with defaults from scene-level `caption_defaults`. `font` is the font family
(best-effort per engine — e.g. Blender needs a loadable font file). Defaults:
size scales with the plate, color `#222222`, font = the bundled `vexy-stax.ttf`
(Zalando Sans Expanded) shipped with the Python package; the JS/browser engine
matches it with the Google Font "Zalando Sans" at wdth 125 / wght 500 (issue 328).

### 2.3 Determinism

`version`, `easing` names, and default values are normative so that all four
renderers (3 py engines + JS) produce visually equivalent output. Shared easing
set: `linear`, `easeInOutCubic` (default), `easeOutCubic`, `easeInCubic`. The
Blender engine maps these to Bezier handles; pygfx/JS evaluate the cubic
directly. Unknown fields are rejected by the parser (fail-loud at the boundary —
"parse, don't validate").

---

## 3. View geometry (normative)

Both packages compute camera and spacing from the same formulas (Python
`geometry.py` and JS `geometry.js`, verified numerically identical) so the
engines agree. Let `N` = slide count, plate dimensions in points = pixel
dimensions.

**Coordinate frame (three.js Y-up).** `X` = plate width (centered at 0); `Y` =
vertical/up (plates centered at `Y = 0`, the vertical middle of the tallest
slide; floor just below `Y = -h/2`); `Z` = depth/stacking — front plate at
`Z = 0`, index 0 (farthest) at `Z = -stack_depth`, `+Z` toward the viewer; deck
center at `Z = -stack_depth/2`. Both renderers (Blender's render script and the
JS three.js stage) build the scene in this one frame. Both cameras are
perspective throughout (never orthographic) to avoid type-switch artifacts during
animation; near plane scales as `near = max(1, distance · 0.005)` to avoid
depth-buffer flashing (legacy `SCENE.md §9`).

**Compact view** — head-on, plates at `MIN_GAP = 3 pt`, **dual-axis crop-free fit**
(issue 302 §1):
- Camera sits head-on on `+Z` in front of the deck center, aimed at it:
  `position = (0, 0, target_z + distance)`.
- For a `"P%"` distance, the frontmost plate (`Z = 0`, size `scene.size`) is fit so the
  *limiting* axis touches `P%` of the frame and the other axis only ever has extra
  padding — never a crop — regardless of viewport/scene aspect mismatch. With
  `θ_h = camera.fov` (horizontal), `θ_v = 2·arctan(tan(θ_h/2) / aspect)`,
  `aspect = scene.size.width / scene.size.height`:

  ```
  d_w = scene.size.width  / (2·tan(θ_h/2)·(P/100))
  d_h = scene.size.height / (2·tan(θ_v/2)·(P/100))
  d_fit = max(d_w, d_h)        # the limiting axis touches exactly P%
  distance = d_fit + depth/2   # depth = stack_depth(compact)
  ```
- A numeric/`"500"` distance is taken as absolute points (no fit).

**Expanded view** — angled hero shot, **margins matched to the projected gap**
(issue 302 §2):
- Plates spaced by `gap` (per-slide override allowed) ⇒ `stack_depth = Σ gaps[1:]`.
- Base target = deck center `(0, 0, -stack_depth/2)`.
- Direction target→camera from azimuth `angle` + `elevation`
  `(-sin az·cos el, sin el, cos az·cos el)`; head-on (az=0) is `+Z`, positive az
  swings toward `-X`, elevation lifts `+Y`.
- The camera **distance** and a horizontal **re-centering pan** are solved so that, in
  the projected image, the left margin (frame edge → leftmost plate) and the right
  margin (rightmost plate → frame edge) are *each equal to the projected gap* — the
  mean horizontal NDC stagger between adjacent plate centers. Because the angled deck
  projects asymmetrically, the camera is panned along its `right` axis (shifting
  `position` and `target` together, preserving the look direction) until the projected
  span is centered (left margin == right margin), then the distance is found by a
  deterministic bisection where `margin − gap` is monotone (margin grows with distance,
  gap shrinks). A vertical-fit floor (`V_FILL = 0.98`) keeps the deck from cropping
  top/bottom. The same bisection runs identically in Python and JS. Framing uses
  `scene.size` as the nominal plate size so Python and JS agree exactly.

**Transition** — interpolate camera position, target, per-plate spacing, and
per-slide opacity from compact→expanded endpoints with the easing curve;
captions fade per §2.2.

---

## 4. Repository layout

```
vexy-stax-dev/
├── SPEC.md                      # this file
├── TODO.md                      # flat actionable task list
├── build.sh install.sh publish.sh   # umbrella scripts → call both sub-repos
├── schema/
│   ├── vexy-stax-scene.schema.json
│   └── examples/airbl.scene.json     # canonical example (points at the py testdata)
├── vexy-stax-py/                # → github.com/vexyart/vexy-stax-py (PyPI)
│   ├── pyproject.toml           # uv + hatch + hatch-vcs
│   ├── build.sh install.sh publish.sh example.py   # example.py → all 3 engines
│   ├── testdata/airbl-lores/    # shared test slides (020 back … 090 front)
│   ├── testdata/airbl.scene.json    # repo-local example scene (slides relative)
│   ├── src/vexy_stax/
│   │   ├── __init__.py  __main__.py  cli.py
│   │   ├── scene.py             # pydantic v2 scene model + loader
│   │   ├── geometry.py          # §3 camera/spacing/opacity math (engine-agnostic)
│   │   ├── engines/
│   │   │   ├── base.py          # Engine protocol: render_image / render_video
│   │   │   ├── blender.py + _blender_render.py   # two-process renderer driving headless Blender
│   │   │   ├── pygfx.py         # fast off-screen GPU renderer using WGPU
│   │   │   └── playwright.py    # drives vexy-stax-js headless
│   │   └── images.py  juicy.py  # Pillow overlay compositing and color matching
│   ├── tests/  outputs/
├── vexy-stax-js/                # → github.com/vexyart/vexy-stax-js (npm)
│   ├── package.json  vite.config.js
│   ├── build.sh install.sh publish.sh example.sh   # example.sh → image/video/playable/scrollspy
│   ├── testdata/airbl-lores/    # real copy (not symlink) for standalone publish + airbl.scene.json
│   ├── src/
│   │   ├── index.js             # ESM public API (§6.1)
│   │   ├── element.js           # <vexy-stax> Web Component (§6.2)
│   │   ├── global.js            # window.VexyStax build entry (§6.3)
│   │   ├── scene.js             # shared scene parser (mirrors scene.py)
│   │   ├── geometry.js          # §3 math (mirrors geometry.py)
│   │   ├── stage.js             # three.js scene/plates/floor/captions (adapts old js)
│   │   ├── transition.js        # morph driver (GSAP/rAF)
│   │   ├── scrollspy.js         # IntersectionObserver + scroll → progress (§6.4)
│   │   └── export.js            # image (canvas) + video (WebCodecs/MediaRecorder)
│   └── tests/  (node --test + playwright)
└── i.vexy.art/dev/vexy-stax/    # showcase, analogous to ../lines-nano (§7)
```

---

## 5. vexy-stax-py

### 5.1 Engine abstraction

```python
class Engine(Protocol):
    name: str
    def render_image(self, scene: Scene, view: View, out: Path) -> None: ...
    def render_video(self, scene: Scene, out: Path) -> None: ...   # uses scene.transition
```

`geometry.py` produces, from a `Scene`, the per-frame camera + per-slide spacing
+ per-slide opacity that every engine consumes — so the three engines share the
math and only differ in how they draw.

### 5.2 CLI

All subcommands and options map to class methods of `vexy_stax.cli.Stax`:

```bash
vexy-stax dir2scene DIRECTORY --out scene.json       # generate scene JSON from directory
vexy-stax render    SCENE.json --view expanded --engine blender --out beauty.png
vexy-stax render    SCENE.json --view compact  --engine pygfx   --out stack.png
vexy-stax video     SCENE.json --engine blender --out morph.mp4
vexy-stax overlay   SCENE.json --out flat.png        # pure-Pillow flat composite
vexy-stax engines                                    # list available engines
```

`--engine` ∈ `{blender, pygfx, playwright}`. Defaults: still ⇒ pygfx (fast),
video ⇒ blender (quality). Engine availability is probed; a missing engine
fails with an actionable message (not a crash).

### 5.3 Engines

- **blender** — two-process renderer. The CLI builds a JSON config, then spawns
  `blender --background --python _blender_render.py` to compile the scene.
  Maps `expanded` to beauty, and `compact` to stack views. Drives plate opacity
  via material keyframes, and handles caption text objects. Uses Eevee for `--turbo`, Cycles
  otherwise.
- **pygfx** — GPU-accelerated renderer. Builds an off-screen canvas using WGPU and renders
  to PNG. Renders videos via frame sequence compiled with ffmpeg.
- **playwright** — launch headless Chromium, load a thin harness page that
  imports `vexy-stax-js`, feed the scene, capture canvas screenshot (image) or
  drive the animation frame-by-frame (video). Pixel-parity check against JS.

### 5.4 Utility modules

- `images.py` handles 2D overlay compositing using Pillow.
- `juicy.py` matches colors between the 3D renders and the 2D overlays via per-channel linear color correction.

---

## 6. vexy-stax-js

Three usage modes, mirroring `lines-nano` (which ships
`vexy-lines-nano.element.js` as `<script type="module">`, defines
`<vexy-lines-nano>` with `el.config = {}`, and exposes `window.VexyLinesNano`).

### 6.1 ESM API (`src/index.js`)

```js
import { VexyStax, loadScene, renderImage, renderVideo } from "vexy-stax-js";
const stax = new VexyStax(container, scene);   // mounts a three.js canvas
await stax.setView("expanded");                 // or "compact"
await stax.transition("expand_collapse");       // playable animation
const blob = await stax.toImage({ scale: 2 });  // single image
const mp4  = await stax.toVideo();              // video (WebCodecs, MediaRecorder fallback)
stax.scrollspy({ trigger: "#section" });        // scroll-driven transition
```

### 6.2 Web Component (`src/element.js`)

```html
<script type="module" src="./vexy-stax-v1/vexy-stax.element.js"></script>
<vexy-stax scene="scene.json" view="expanded" mode="scrollspy"></vexy-stax>
<script type="module">
  const el = document.querySelector("vexy-stax");
  el.config = { /* inline scene object */ };
  el.addEventListener("ready", () => el.transition("expand"));
</script>
```

Attributes: `scene` (URL), `view`, `mode` (`static`|`playable`|`scrollspy`),
`width`, `height`. Property `config` accepts an inline scene object (overrides
`scene`). Events: `ready`, `transitionstart`, `transitionend`.

### 6.3 Global (`src/global.js` → IIFE/UMD build)

```html
<script src="./vexy-stax-v1/vexy-stax.global.js"></script>
<script>const stax = new VexyStax.VexyStax(el, scene);</script>
```

### 6.4 Scrollspy

`scrollspy.js` maps scroll progress over a trigger region to transition progress
`[0,1]` (IntersectionObserver for activation + scroll/`requestAnimationFrame` for
progress; CSS `scroll-timeline` when available). Default mapping: 0 ⇒ compact,
1 ⇒ expanded for `expand`; symmetric for the round-trips. Respects
`prefers-reduced-motion` (snaps to endpoints).

### 6.5 Stack rendering

`stage.js` adapts the three.js scene from `vexy-stax-old/vexy-stax-js`
(`SceneComposition`, `FloorManager`, `CameraController`, `camera/animation.js`),
reduced to the two views + transitions + opacity + captions. Captions are
THREE.Sprite objects drawn right-aligned (`ctx.textAlign="right"`) with
`sprite.center=(1,0.5)` (right-middle anchor) so each sprite's right edge sits
at `captionAnchorX` (geometry.js), positioned at `Y=0`/plate-Z. Opacity is
driven exclusively by `captionOpacities(scene,t)` (live view) or
`state.captionOpacities` (video frames). Build: vite, ESM + IIFE outputs,
`three` and `gsap` deps retained, Tweakpane editor UI dropped from the shipped
library (kept only in the demo's editor page if useful).

---

## 7. Demo page (`i.vexy.art/dev/vexy-stax/`)

Analogous to `lines-nano`: a static folder served as-is, importing the built
`vexy-stax.element.js` via `<script type="module">`. Pages:

- `index.html` — landing; one `<vexy-stax>` hero + the three usage snippets.
- `demo-component.html` — Web Component attribute/property examples.
- `demo-scrollspy.html` — full-height scroll story driving expand↔collapse.
- `demo-playable.html` — play/replay transition button.
- `editor.html` — optional Tweakpane scene editor exporting scene JSON.

Loads slides from `../../../testdata/airbl-lores/` (or bundled copies).

---

## 8. Testing & verification

- **Python**: `uvx hatch test`; unit tests for `scene.py`/`geometry.py` (pure,
  engine-free); engine smoke tests gated by availability marks
  (`@pytest.mark.blender` etc.); `test.sh` runs lint+format+type+tests then a
  functional render of `airbl-lores` per engine.
- **JS**: `node --test` for `scene.js`/`geometry.js`/`transition.js`/`stage.js`
  (including caption layout: anchor, textAlign, position, opacity, visibility);
  Playwright E2E for the component, exports, and scrollspy.
- **Cross-engine parity**: render compact+expanded stills of `airbl-lores` with
  every engine and the JS path; compare structurally (SSIM threshold) in G007
  (VerifyIterate).
- **Determinism**: `geometry.py` and `geometry.js` tested against the same
  fixture vectors so the math provably matches.

---

## 9. Completed implementation phases

All phases below were completed during issues 301 and 302.

1. Scene format v1 + JSON schema + example scene from `airbl-lores`.
2. `vexy-stax-py` scaffold (pyproject, scene.py, geometry.py, engine base, CLI).
3. Blender engine (expanded/compact + opacity + captions; image + video).
4. pygfx engine (GPU off-screen via WGPU).
5. `vexy-stax-js` scaffold (vite, scene.js, geometry.js, stage.js; ESM + element
   + global).
6. JS ops (image, video, playable, scrollspy).
7. Playwright engine (drives the JS build in headless Chromium).
8. Demo page (`i.vexy.art/dev/vexy-stax/`).
9. Issue 302: dual-axis compact framing, margin-matched expanded framing, caption
   model + staggered fade math, caption render in all engines, smooth video
   defaults (30 fps / 2 s).
