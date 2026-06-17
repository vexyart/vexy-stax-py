<!-- this_file: README.md -->

# vexy-stax

Render a deck of layered PNG slides as 3D glass plates — in two views and the
transitions between them — from a single shared JSON scene format. This is the
offline Python package; a browser sibling (`vexy-stax-js`) consumes the same
scene format. See the repo-level `SPEC.md` for the binding contract.

This package implements the scene model, geometry math, CLI, and three fully functional render backends: Blender, pygfx, and Playwright.

## Install

```bash
uv venv --python 3.12 && uv sync
```

## Concepts

- A **scene** is an ordered list of **slides** (back-to-front; index 0 is
  farthest from the camera) plus camera, floor, and transition settings.
- Two **views**: `expanded` (angled, plates spaced by `gap`, captions on) and
  `compact` (head-on, plates collapsed to `MIN_GAP ≈ 3 pt`).
- A **transition** morphs between the views (`expand`, `collapse`,
  `expand_collapse`, `collapse_expand`), interpolating camera, spacing, and
  per-slide opacity with a shared easing curve.

## CLI

```bash
vexy-stax dir2scene assets/ --out scene.json             # generate scene JSON from directory
vexy-stax render    scene.json --view expanded --engine pygfx   --out beauty.png
vexy-stax render    scene.json --view compact  --engine blender --out stack.png
vexy-stax video     scene.json --engine blender --out morph.mp4
vexy-stax overlay   scene.json --out flat.png          # pure-Pillow flat composite
vexy-stax engines                                      # list available engines
```

Defaults: still ⇒ `pygfx`, video ⇒ `blender`. A missing/unimplemented engine
fails with an actionable message, not a crash.

## Library

```python
from vexy_stax.scene import load_scene
from vexy_stax import geometry as g

scene = load_scene("scene.json")          # validates + resolves slide paths
plan = g.frame_plan(scene)                 # per-frame camera/spacing/opacity
pose = g.expanded_camera(scene)            # CameraPose dataclass
```

`vexy_stax.scene` is a strict pydantic v2 model (`extra="forbid"` everywhere —
unknown fields fail loud at the boundary). `vexy_stax.geometry` holds the pure,
engine-agnostic view math (SPEC.md §3), mirrored by the JS `geometry.js` against
shared fixture vectors.

## Layout

```
src/vexy_stax/
├── scene.py        # pydantic v2 scene model + loader
├── geometry.py     # §3 camera/spacing/opacity math (pure, engine-agnostic)
├── engines/        # base.py protocol + registry; blender, pygfx, and playwright renderers
├── images.py       # Composites 2D flat preview overlays using Pillow
├── juicy.py        # Matches colors between 3D renders and 2D overlays
└── cli.py          # fire + rich CLI
```

## Test

```bash
uv run pytest -q
```

## License

MIT.
