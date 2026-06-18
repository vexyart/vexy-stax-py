---
title: Home
nav_order: 1
---

# vexy-stax

Render a deck of layered PNG slides as 3D glass plates — in two views and the transitions between them — from a single shared JSON scene format.

**vexy-stax-py** is the offline Python package that renders stills and video via three interchangeable engines (Blender, pygfx, Playwright). A browser sibling, **vexy-stax-js**, consumes the same scene format and renders in the browser as a Web Component, ESM module, or classic-script global.

## What it does

Given a set of layered PNG images and a JSON scene file, vexy-stax renders:

- **Expanded view** — an angled hero shot with plates spaced apart and captions visible
- **Compact view** — a head-on stack with plates collapsed tight
- **Transition video** — a morphing animation between the two views, with per-slide opacity, camera movement, and staggered caption fade

All geometry — camera placement, plate spacing, caption positioning — is computed from the same formulas in both the Python and JavaScript packages, so renders are visually identical across all four renderers (three Python engines + JS).

## Live demos

See the browser renderer (**vexy-stax-js**) in action:

- [Animated demo](https://vexy.dev/vexy-stax-js/playable.html) — play the compact ↔ expanded transition, or toggle the two views by hand
- [Scrollspy demo](https://vexy.dev/vexy-stax-js/scrollable.html) — a scroll-driven story where the deck rises into view and unfolds as you scroll
- [vexy-stax-js home](https://vexy.dev/vexy-stax-js/) — the JS package landing page (Web Component · ESM · global script)

## Quick start

```bash
# Install
uv venv --python 3.12 && uv sync

# Generate a scene from a folder of PNGs
vexy-stax dir2scene assets/ --out scene.json

# Render expanded view (pygfx, fast)
vexy-stax render scene.json --view expanded --out beauty.png

# Render transition video (blender, quality)
vexy-stax video scene.json --out morph.mp4
```

## Documentation chapters

| Chapter | Topic |
|---------|-------|
| [Introduction & Concept](01-introduction.md) | What vexy-stax is and what problems it solves |
| [Core Concepts](02-concepts.md) | Plates, deck, views, transitions, floor |
| [Scene Format Overview](03-scene-format-overview.md) | JSON structure and top-level fields |
| [Scene Format Reference](04-scene-format-reference.md) | Every field documented |
| [Installation](05-installation.md) | uv/pip install, prerequisites |
| [CLI Usage](06-cli.md) | Commands, flags, examples |
| [Rendering Engines](07-engines.md) | blender, pygfx, playwright — tradeoffs |
| [View Geometry & Framing](08-geometry.md) | Camera math, compact fit, expanded framing |
| [Captions & Layout](09-captions.md) | Caption plates, fade, stagger |
| [vexy-stax-js](10-js-library.md) | Web Component, ESM, scrollspy |
| [Python API](11-python-api.md) | load_scene, engines, frame_plan |
| [Architecture & Contributing](12-architecture.md) | Repo layout, parity testing, contributing |

## License

MIT — Copyright 2026 Fontlab Ltd.
