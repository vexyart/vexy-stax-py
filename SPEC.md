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

This document is the contract. It supersedes the legacy specs in
`vexy-stax2-py/SPEC.md`, `vexy-stax-old/SCENE.md`, and
`vexy-stax-old/docs/PROJECT_FORMAT.md`, which remain as references.

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
  "floor": {
    "color": "#f2f2f2",
    "opacity": 1.0,
    "reflectivity": 0.5
  },
  "background": "#ffffff",
  "juicy": false,                       // py only: per-channel color match (see §5.4)
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

### 2.2 Captions (issue 301 §5)

`slide.caption` places a text label beneath the plate. `show_in` is
`"expanded"` (default), `"compact"`, `"both"`, or `"none"`. Captions sit below the
floor line, centered under the plate, and fade with the same morph factor as the
view they belong to (a caption `show_in: "expanded"` is invisible in compact and
fades in as the deck expands). Optional `caption.style`
(`{ size, color, font }`) is engine-best-effort; defaults come from scene-level
`caption_defaults` if present.

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

**Compact view** — head-on, plates at `MIN_GAP = 3 pt`:
- Camera sits head-on on `+Z` in front of the deck center, aimed at it:
  `position = (0, 0, target_z + distance)`.
- `distance` = absolute points or `"P%"` of viewport width.

**Expanded view** — angled hero shot:
- Plates spaced by `gap` (per-slide override allowed) ⇒ `stack_depth = Σ gaps[1:]`.
- Target = deck center `(0, 0, -stack_depth/2)`.
- Direction target→camera from azimuth `angle` + `elevation`
  `(-sin az·cos el, sin el, cos az·cos el)`; head-on (az=0) is `+Z`, positive az
  swings toward `-X`, elevation lifts `+Y`.
- Distance fits the **plate-deck bounding box** (not the floor): the plate
  corners are projected onto the camera right/up axes and `distance` is chosen so
  the deck fills `FILL = 0.85` of the frame on its tighter axis. (The legacy
  floor-diagonal fit let a deep floor shrink the plates to a speck.) Framing uses
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
│   ├── build.sh install.sh publish.sh example.sh   # example.sh → all 3 engines
│   ├── testdata/airbl-lores/    # shared test slides (020 back … 090 front)
│   ├── testdata/airbl.scene.json    # repo-local example scene (slides relative)
│   ├── src/vexy_stax/
│   │   ├── __init__.py  __main__.py  cli.py
│   │   ├── scene.py             # pydantic v2 scene model + loader
│   │   ├── geometry.py          # §3 camera/spacing/opacity math (engine-agnostic)
│   │   ├── engines/
│   │   │   ├── base.py          # Engine protocol: render_image / render_video
│   │   │   ├── blender.py + _blender_render.py   # two-process (adapts vexy-stax2)
│   │   │   ├── pygfx.py         # adapts vexy-stax-old/vexy-stax-py
│   │   │   └── playwright.py    # drives vexy-stax-js headless
│   │   └── images.py  juicy.py  # reused from vexy-stax2
│   ├── tests/  outputs/
├── vexy-stax-js/                # → github.com/vexyart/vexy-stax-js (npm)
│   ├── package.json  vite.config.js
│   ├── build.sh install.sh publish.sh example.sh   # example.sh → image/video/playable/scrollspy
│   ├── testdata/airbl-lores → ../../vexy-stax-py/testdata/airbl-lores  # symlink + airbl.scene.json
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

### 5.2 CLI (fire + rich)

```
vexy-stax render  SCENE.json --view expanded --engine blender --out beauty.png
vexy-stax render  SCENE.json --view compact  --engine pygfx   --out stack.png
vexy-stax video   SCENE.json --engine blender --out morph.mp4
vexy-stax overlay SCENE.json --out flat.png          # pure-Pillow flat composite
```

`--engine` ∈ `{blender, pygfx, playwright}`. Defaults: still ⇒ pygfx (fast),
video ⇒ blender (quality). Engine availability is probed; a missing engine
fails with an actionable message (not a crash).

### 5.3 Engines

- **blender** — adapt `vexy-stax2-py/src/vexy_stax2/render.py` (two-process:
  CLI builds JSON config, `blender --background --python _blender_render.py`).
  Map `expanded`→beauty, `compact`→stack. Add opacity morph (drive plate alpha
  via material/keyframes) and caption text objects. Eevee for `--turbo`, Cycles
  otherwise.
- **pygfx** — adapt `vexy-stax-old/vexy-stax-py` pygfx renderer; GPU, fast,
  off-screen canvas → PNG; video via frame sequence + ffmpeg.
- **playwright** — launch headless Chromium, load a thin harness page that
  imports `vexy-stax-js`, feed the scene, capture canvas screenshot (image) or
  drive the animation frame-by-frame (video). Pixel-parity check against JS.

### 5.4 Reused as-is

`images.py` (overlay/compositing) and `juicy.py` (per-channel color match)
copied from `vexy-stax2-py` with only `this_file`/import path updates.

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
reduced to the two views + transitions + opacity + captions. Build: vite, ESM +
IIFE outputs, `three` and `gsap` deps retained, Tweakpane editor UI dropped from
the shipped library (kept only in the demo's editor page if useful).

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
- **JS**: `node --test` for `scene.js`/`geometry.js`/`scrollspy.js`; Playwright
  E2E for the component, exports, and scrollspy.
- **Cross-engine parity**: render compact+expanded stills of `airbl-lores` with
  every engine and the JS path; compare structurally (SSIM threshold) in G010.
- **Determinism**: `geometry.py` and `geometry.js` tested against the same
  fixture vectors so the math provably matches.

---

## 9. Reuse map

| New code                         | Adapted from                                              |
|----------------------------------|-----------------------------------------------------------|
| `engines/blender.py`, `_blender_render.py` | `vexy-stax2-py/src/vexy_stax2/render.py`, `cli.py` |
| `images.py`, `juicy.py`          | `vexy-stax2-py/src/vexy_stax2/{images,juicy}.py`          |
| `engines/pygfx.py`               | `vexy-stax-old/vexy-stax-py/` pygfx renderer              |
| `engines/playwright.py`          | `vexy-stax-old/vexy-stax-py/` playwright renderer         |
| `stage.js`, `geometry.js`, `transition.js` | `vexy-stax-old/vexy-stax-js/src/{core,camera,scene}/` |
| scene format                     | `vexy-stax2-py` project JSON + `vexy-stax-old/SCENE.md`   |
| demo page                        | `i.vexy.art/dev/lines-nano/`                              |

---

## 10. Implementation phases (→ TODO.md)

1. Scene format v1 + JSON schema + example scene from `airbl-lores`.
2. `vexy-stax-py` scaffold (pyproject, scene.py, geometry.py, engine base, CLI).
3. Blender engine (expanded/compact + opacity + captions; image + video).
4. pygfx engine.
5. `vexy-stax-js` scaffold (vite, scene.js, geometry.js, stage.js; ESM + element
   + global) — must precede the Playwright engine which depends on it.
6. JS ops (image, video, playable, scrollspy).
7. Playwright engine (drives the JS build).
8. Demo page.
9. Integration: cross-engine parity, tests green, docs, quality gate.

Note: ordering differs slightly from the story IDs — the Playwright engine (G006)
depends on the JS scaffold (G007), so G007/G008 land before G006 in practice.
