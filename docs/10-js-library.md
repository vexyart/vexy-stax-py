---
title: vexy-stax-js
nav_order: 11
---

# vexy-stax-js

**vexy-stax-js** is the browser counterpart to vexy-stax-py. It consumes the same JSON scene format and renders in the browser via three.js. It ships three ways:

| Mode | File | Usage |
|------|------|-------|
| ESM module | `dist/vexy-stax.element.js` | `import { VexyStax } from "vexy-stax-js"` |
| Web Component | `dist/vexy-stax.element.js` | `<vexy-stax scene="…">` |
| Global script | `dist/vexy-stax.global.js` | `new VexyStax.VexyStax(el, scene)` |

Source: `github.com/vexyart/vexy-stax-js` · npm: `vexy-stax-js`

> **No build step?** Load it straight from the jsDelivr CDN:
> `https://cdn.jsdelivr.net/npm/vexy-stax-js@3.1.2/dist/vexy-stax.element.js` (Web Component / ESM)
> or `…/dist/vexy-stax.global.js` (global script). Every snippet below works verbatim from the CDN.

---

## Easiest path (issue 341)

You do not need a scene JSON to get started — pass a **list of slide image URLs** and vexy-stax-js
fills in sensible defaults.

**Web Component** — the `slides` attribute (space/newline-separated URLs; local, `data:`, or remote):

```html
<script type="module" src="https://cdn.jsdelivr.net/npm/vexy-stax-js@3.1.2/dist/vexy-stax.element.js"></script>

<vexy-stax
  slides="layer-0.png layer-1.png https://example.com/layer-2.png"
  view="compact" mode="playable">
</vexy-stax>
```

**ES module** — `createStax(elOrSelector, opts)` (mirrors the one-call factory pattern):

```js
import { createStax } from "vexy-stax-js";

const stax = await createStax("#stage", {
  slides: ["layer-0.png", "https://example.com/layer-1.png"],
  gap: 480,                    // expanded plate spacing (camera.gap shortcut)
  transition: "expand_collapse",
  mode: "playable",            // play the transition once when ready
});
```

`opts` accepts `{ slides | scene, view, mode, trigger, width, height, clickToggle, baseUrl }` plus
any scene override (`size`, `camera`, `gap`, `transition`, `background`, `captions`, `floor`, `edge`,
`caption_defaults`, …) — forwarded to `makeScene`.

**`makeScene(slides, opts)`** builds a valid scene object from a bare URL list (or `{src, caption,
opacity, gap}` objects), filling defaults so even `makeScene(["a.png", "b.png"])` renders:

```js
import { makeScene, VexyStax } from "vexy-stax-js";
const scene = makeScene(["a.png", "b.png", "c.png"], { gap: 480, transition: "expand_collapse" });
const stax = new VexyStax(container, scene);
```

### Click-to-toggle (issue 342)

For any interactive container (the `<vexy-stax>` element and every `createStax` instance),
**clicking anywhere inside fluently toggles** compact↔expanded — if not compact it collapses, if
compact it expands. It reuses the morph driver (a smooth `expand`/`collapse` leg — never a snap) and
is **on by default**. Opt out with the `click-toggle="false"` attribute or `createStax(el, {
clickToggle: false })`. In the scrollspy demo it works **on top of** the scroll-driven morph.

Call it imperatively too: `await stax.toggleView()` (or `el.toggleView()`).

### Scene-in-init (issue 342)

Pass a full scene **object** at initialization — no URL, no fetch:

```js
// ESM
await createStax("#stage", { scene: { version: 1, slides: [{ src: "a.png" }] }, view: "expanded" });

// Web Component (property; also accepts the `config` property / attribute)
document.querySelector("vexy-stax").scene = { version: 1, slides: [{ src: "a.png" }, { src: "b.png" }] };
```

### Remote slide images

Slide `src` may be a local path, a `data:` URI, or a **remote `http(s)` URL**. The three.js texture
loader uses `crossOrigin="anonymous"`, so images from a CORS-enabled server load **and** keep the
canvas exportable (`toImage` / `toVideo`).

---

## Quick start

```bash
npm install
npm run dev        # vite dev server with HMR
npm run build      # -> dist/vexy-stax.element.js + dist/vexy-stax.global.js
npm test           # unit + Playwright E2E
```

---

## ESM API

Import from `vexy-stax-js` in any ES module context:

```js
import { VexyStax, loadScene, renderImage, renderVideo } from "vexy-stax-js";

// Load and parse a scene JSON
const scene = await loadScene("scene.json");

// Mount a three.js canvas into a container element
const stax = new VexyStax(container, scene);

// Switch to a view (no animation)
await stax.setView("compact");
await stax.setView("expanded");

// Play a transition animation
await stax.transition("expand_collapse");

// Export a still image
const blob = await stax.toImage({ scale: 2 });
const url = URL.createObjectURL(blob);

// Export a video (WebCodecs, MediaRecorder fallback)
const mp4 = await stax.toVideo();

// Attach scroll-driven transition
stax.scrollspy({ trigger: "#hero-section" });
```

### `VexyStax` constructor

```js
const stax = new VexyStax(container, scene);
```

- `container`: a DOM element. vexy-stax mounts a `<canvas>` inside it and sizes the canvas to the container.
- `scene`: a parsed scene object (from `loadScene()`) or a plain JS object matching the scene format.

### `loadScene(url)`

Fetches and parses a scene JSON from a URL. Validates it with the same strict parser as the Python package (unknown fields are rejected).

```js
const scene = await loadScene("./scene.json");
```

### `stax.setView(view)`

Instantly switches to `"expanded"` or `"compact"` with no animation. Returns a Promise that resolves when the canvas has been updated.

### `stax.transition(kind)`

Plays the named transition animation (`"expand"`, `"collapse"`, `"expand_collapse"`, `"collapse_expand"`). Uses the scene's `transition` settings (duration, fps, easing, wait). Returns a Promise that resolves when the animation completes.

### `stax.toImage({ scale })`

Renders the current view at `scale × scene.size` and returns a `Blob` (PNG). Default `scale: 1`.

### `stax.toVideo()`

Renders the full transition as a video. Uses WebCodecs when available, MediaRecorder as a fallback. Returns a `Blob` (MP4 or WebM depending on browser support).

### `stax.scrollspy({ trigger })`

Attaches a scroll-driven transition. `trigger` is a CSS selector or element. As the trigger element scrolls through the viewport, the transition progress is mapped to `[0, 1]` (IntersectionObserver for activation, scroll/rAF for progress). Respects `prefers-reduced-motion` (snaps to endpoints instead of animating).

---

## Web Component

The `<vexy-stax>` custom element auto-registers when the element module is loaded.

```html
<script type="module" src="./dist/vexy-stax.element.js"></script>

<!-- Load from URL, expanded view, static -->
<vexy-stax scene="scene.json" view="expanded" mode="static"></vexy-stax>

<!-- Scroll-driven -->
<vexy-stax scene="scene.json" mode="scrollspy"></vexy-stax>

<!-- Playable: auto-plays transition on load -->
<vexy-stax scene="scene.json" mode="playable"></vexy-stax>
```

### Attributes

| Attribute | Values | Default | Description |
|-----------|--------|---------|-------------|
| `scene` | URL string | — | URL to the scene JSON file |
| `slides` | space/newline-separated URLs | — | Easy path: build a scene from a bare image-URL list (issue 341) |
| `captions` | `true` \| `false` | `true` | Toggle caption plates (used with `slides`) |
| `view` | `expanded` \| `compact` | `expanded` | Initial view |
| `mode` | `static` \| `playable` \| `scrollspy` | `static` | Interaction mode |
| `click-toggle` | `true` \| `false` | `true` | Click-to-toggle compact↔expanded (issue 342); set `false` to opt out |
| `width` | CSS dimension | container width | Canvas width override |
| `height` | CSS dimension | container height | Canvas height override |

Source precedence: inline `config`/`scene` **object** → `scene` URL → `slides` list.

### `config` property

Set an inline scene object (overrides the `scene` attribute):

```js
const el = document.querySelector("vexy-stax");
el.config = {
  version: 1,
  slides: [
    { src: "./layer-0.png", caption: { text: "Background" } },
    { src: "./layer-1.png", caption: { text: "Content" } }
  ]
};
```

### Events

| Event | When |
|-------|------|
| `ready` | Scene is loaded and first frame rendered |
| `transitionstart` | A transition begins |
| `transitionend` | A transition completes |

```js
const el = document.querySelector("vexy-stax");
el.addEventListener("ready", () => {
  el.transition("expand");
});
el.addEventListener("transitionend", (e) => {
  console.log("done:", e.detail);
});
```

---

## Global script

For environments without ES module support:

```html
<script src="./dist/vexy-stax.global.js"></script>
<script>
  const scene = await VexyStax.loadScene("scene.json");
  const stax = new VexyStax.VexyStax(document.getElementById("stage"), scene);
  stax.setView("expanded");
</script>
```

The global build exposes `window.VexyStax` with the same API as the ESM module.

---

## Scrollspy

`src/scrollspy.js` maps scroll progress over a trigger region to transition progress `[0, 1]`:

- Uses **IntersectionObserver** for activation (starts/stops tracking when the trigger enters/leaves the viewport).
- Uses **scroll event + `requestAnimationFrame`** for smooth progress updates.
- Uses **CSS `scroll-timeline`** when available for the smoothest experience.

Default mapping for `expand`: scroll progress `0 → 1` maps to `compact → expanded`. For `collapse_expand`, `0 → 0.5 → 1` maps to `expanded → compact → expanded`.

`prefers-reduced-motion`: when the user has requested reduced motion, the component snaps to the endpoint of the transition instead of animating.

---

## Rendering internals

### `stage.js` — three.js scene

`stage.js` builds the three.js scene:

- **Plates** — `PlaneGeometry` meshes with `MeshBasicMaterial` (the PNG texture), positioned along `Z` from `geometry.js` calculations.
- **Floor** — an infinite plane with a blurred reflection texture.
- **Captions** — `THREE.Sprite` objects drawn with `ctx.textAlign = "right"` and `sprite.center = (1, 0.5)` (right-middle anchor), so each sprite's right edge lands at `captionAnchorX` from `geometry.js`.
- **Camera** — always perspective (never orthographic) to avoid type-switch artifacts during animation.

### `geometry.js` — view math

Mirrors `vexy-stax-py/src/vexy_stax/geometry.py` exactly. Exports `compactCamera`, `expandedCamera`, `frameStateAt`, `captionOpacities`, `ease`, and all caption geometry helpers. Tested against the same fixture vectors as the Python package.

### `transition.js` — morph driver

A `requestAnimationFrame`-based morph driver. Given a transition kind and scene, drives `t ∈ [0,1]` through each leg, applying the easing curve and calling `stage.applyFrameState(state)` on each frame. Used by both `stax.transition()` and `stax.scrollspy()`.

### `export.js` — image and video capture

- **Image**: reads the three.js canvas via `canvas.toBlob("image/png")` at the requested scale.
- **Video**: uses the WebCodecs `VideoEncoder` API when available; falls back to `MediaRecorder` with `captureStream()`. Output is H.264 MP4 (WebCodecs) or the browser's preferred MediaRecorder codec (WebM on Chrome/Firefox).

---

## Source layout

```
vexy-stax-js/src/
├── index.js        ESM public API: VexyStax, loadScene, renderImage, renderVideo
├── element.js      <vexy-stax> Web Component
├── global.js       window.VexyStax IIFE build entry
├── scene.js        Scene parser (mirrors scene.py — strict, unknown fields rejected)
├── geometry.js     View math (mirrors geometry.py, numerically identical)
├── stage.js        three.js plates + floor + captions + camera
├── transition.js   rAF morph driver + timeline math
├── scrollspy.js    IntersectionObserver + scroll → progress
└── export.js       canvas → PNG; WebCodecs/MediaRecorder → video
```

---

## Testing

```bash
npm run test:unit       # node --test (scene.js, geometry.js, transition.js, scrollspy.js)
npm run test:e2e        # Playwright: mount, views, image/video export, scrollspy
node verify/run.mjs     # Hard render gate: compact + expanded stills in headless Chromium
python3 verify/gate.py  # PIL pixel variance check (not a blank canvas)
```

The unit tests for `stage.js` cover caption sprite center anchor, `textAlign`, position at `captionAnchorX`, opacity from `captionOpacities`, and visibility threshold — all using a Node.js THREE stub via `registerHooks`.
