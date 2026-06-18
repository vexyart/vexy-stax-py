---
title: Introduction & Concept
nav_order: 2
---

# Introduction & Concept

## What is vexy-stax?

vexy-stax is a renderer that takes a stack of layered PNG images — the kind you would export from a design tool, a compositing pipeline, or a presentation — and renders them as 3D glass plates arranged in a deck.

The deck can be shown in two views:

- **Expanded** — an angled hero shot; plates are spaced apart with depth between them, captions are visible, and the camera sits at an oblique angle so you see the layering clearly.
- **Compact** — a head-on stack; plates collapse together so they appear as a single composite image, captions are hidden.

Between the two views, vexy-stax can render a smooth transition video where the camera orbits, the plates spread apart or collapse, and per-slide opacity changes — all driven by a shared easing curve.

## The problem it solves

Layered artwork — UI mockups, photo composites, design systems — is normally presented either as a flat image (losing the sense of layers) or as an animation sequence (requiring manual After Effects work). vexy-stax automates both: give it a folder of PNG layers, and it produces the hero shot, the compact stack, and the morphing transition with no manual keyframing.

## Two packages, one format

The project ships two packages that consume the same JSON scene format:

| Package | Runtime | Engines | Output |
|---------|---------|---------|--------|
| **vexy-stax-py** | Python 3.12+ | blender, pygfx, playwright | PNG stills, MP4 video |
| **vexy-stax-js** | Browser / Node | three.js | Canvas, PNG blob, WebM/MP4 video, scrollspy |

The scene format is a single JSON file that specifies the slides, camera settings, floor, captions, and transition parameters. Both packages validate it against the same JSON Schema (`schema/vexy-stax-scene.schema.json`) and reject unknown fields at the boundary (fail-loud, parse-don't-validate design).

## How it works at a high level

1. You write (or generate with `dir2scene`) a JSON scene file listing your PNG slides and camera settings.
2. You call `vexy-stax render` (or the Python/JS API) with an engine choice.
3. The engine loads the scene, calls into `geometry.py` / `geometry.js` to compute the camera position and per-plate Z positions, then draws the 3D glass plates.
4. For video, `frame_plan()` produces one `FrameState` per animation frame — each with a camera pose, per-slide gap, opacity, and caption opacity — and the engine renders each frame.

All geometry math is shared between Python and JS (tested against identical fixture vectors), so the four renderers produce visually equivalent output.

## Rendering engines

vexy-stax-py ships three engines, each with different tradeoffs:

- **pygfx** — GPU-accelerated, off-screen, fast (seconds per frame). Default for still images.
- **blender** — Two-process Cycles/Eevee renderer. Highest quality (ray-traced transparency, soft reflections). Default for video.
- **playwright** — Headless Chromium driving the JS renderer. Provides a pixel-parity reference against the browser build.

## Example output

```bash
# Generate scene from assets folder
vexy-stax dir2scene assets/ --out scene.json

# Render expanded hero shot
vexy-stax render scene.json --view expanded --engine pygfx --out beauty.png

# Render compact stack
vexy-stax render scene.json --view compact --engine pygfx --out stack.png

# Render morphing transition
vexy-stax video scene.json --engine blender --out morph.mp4

# Flat Pillow composite (no 3D engine needed)
vexy-stax overlay scene.json --out flat.png
```
