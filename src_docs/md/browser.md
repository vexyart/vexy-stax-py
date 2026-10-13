# vexy-stax-js

[vexy-stax-js](https://vexy.dev/vexy-stax-js/) is the browser counterpart of vexy-stax-py. It reads the same scene format and renders it live with three.js. Its own documentation covers the JavaScript API; this page explains how the two packages relate.

## What the two packages share

| Shared piece | Python | JavaScript |
|--------------|--------|------------|
| Scene format | `vexy_stax/scene.py` (Pydantic) | `src/scene.js` |
| JSON Schema | `schema/vexy-stax-scene.schema.json` | the same schema |
| View math | `vexy_stax/geometry.py` | `src/geometry.js` |

Both parsers reject unknown fields, and both geometry modules implement the formulas in [Geometry](geometry.md), including the bisection solve for the expanded camera. A scene file written for one package renders with the same framing in the other.

There are two deliberate differences:

- `juicy` is a Python-only field; vexy-stax-js ignores it.
- The live browser element passes its container's aspect ratio as `viewport_aspect` to the camera functions, so the deck fills a container whose shape differs from the scene. The offline Python engines render at `scene.size` and use the scene's own aspect ratio.

## What the browser package adds

vexy-stax-js ships as a `<vexy-stax>` Web Component, an ES module and a classic-script global. Beyond stills and video export it can play the transition interactively and drive it from page scrolling. See the live demos:

- [Animated demo](https://vexy.dev/vexy-stax-js/playable.html)
- [Scrollspy demo](https://vexy.dev/vexy-stax-js/scrollable.html)

## The Playwright engine uses the JS build

The `playwright` engine in vexy-stax-py does not draw the plates itself. It loads `vexy-stax-js/dist/vexy-stax.element.js` in headless Chromium, mounts the scene in a `<vexy-stax>` element and captures the canvas. For video it computes `frame_plan()` in Python and pushes each frame state into the page with `stage.applyFrameState`, so Python decides every frame and three.js draws it.

To use it, check out both repositories side by side and build the JS bundle:

```text
github.vexyart/
├── vexy-stax-js/     # npm install && npm run build → dist/vexy-stax.element.js
└── vexy-stax-py/
```

```bash
cd vexy-stax-js
npm install
npm run build
```

Rendering the same scene with `--engine playwright` and with `--engine pygfx` or `--engine blender` is the quickest way to compare the browser output with the offline renderers.
