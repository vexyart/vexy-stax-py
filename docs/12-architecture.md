---
title: Architecture & Contributing
nav_order: 13
---

# Architecture & Contributing

## Repository layout

The vexy-stax project lives in a monorepo (`vexy-stax-dev`) containing both packages:

```
vexy-stax-dev/
├── SPEC.md                          Normative scene format + geometry specification
├── schema/
│   └── vexy-stax-scene.schema.json  JSON Schema (draft 2020-12) for the scene format
├── vexy-stax-py/                    PyPI package (this docs site)
│   ├── pyproject.toml               uv + hatch + hatch-vcs build
│   ├── src/vexy_stax/
│   │   ├── scene.py                 Pydantic v2 scene model
│   │   ├── geometry.py              Pure view math (normative)
│   │   ├── engines/
│   │   │   ├── base.py              Engine protocol + registry
│   │   │   ├── blender.py           Blender two-process renderer
│   │   │   ├── _blender_render.py   Script run inside Blender subprocess
│   │   │   ├── pygfx.py             WGPU off-screen renderer
│   │   │   └── playwright.py        Headless Chromium renderer
│   │   ├── images.py                Pillow flat composite
│   │   ├── juicy.py                 Per-channel color correction
│   │   └── cli.py                   fire + rich CLI
│   ├── tests/                       pytest test suite
│   ├── testdata/airbl-lores/        8 shared test slides (PNG)
│   └── docs/                        This documentation site
└── vexy-stax-js/                    npm package
    ├── src/
    │   ├── geometry.js              View math (mirrors geometry.py exactly)
    │   ├── scene.js                 Scene parser (mirrors scene.py)
    │   ├── stage.js                 three.js plates + floor + captions
    │   ├── transition.js            rAF morph driver
    │   ├── scrollspy.js             IntersectionObserver scroll driver
    │   ├── export.js                Canvas/video export
    │   ├── index.js                 ESM public API
    │   ├── element.js               <vexy-stax> Web Component
    │   └── global.js                window.VexyStax IIFE entry
    └── tests/                       node --test + Playwright E2E
```

---

## Design principles

### Parse, don't validate

Every scene parser (`scene.py`, `scene.js`) uses `extra="forbid"` / `additionalProperties: false`. If a document is accepted, it is a valid scene — the type itself is proof of validity. Unknown fields are rejected at the boundary with a clear error, preventing silent failures from typos in field names.

### Geometry parity: PY ↔ JS

`geometry.py` and `geometry.js` implement the same formulas and are tested against the **same fixture vectors**. This guarantees that a Python-computed `FrameState` and a JS-computed `frameStateAt` produce numerically identical camera poses, gaps, opacities, and caption opacities for the same scene. The playwright engine exploits this: it drives the JS renderer with Python-computed frame states and achieves ≥ 0.96 SSIM parity against all other engines.

Changes to geometry must be made in both files simultaneously and verified by the cross-engine parity tests.

### Engine abstraction

All engines implement the same two-method `Engine` protocol:

```python
class Engine(Protocol):
    name: str
    def render_image(self, scene: Scene, view: View, out: Path) -> None: ...
    def render_video(self, scene: Scene, out: Path) -> None: ...
```

Engines are self-registering (imported once on first use) and availability-probed without importing heavy dependencies at module load time. A missing engine fails with an actionable `KeyError` or `NotImplementedError` — never a silent crash or a traceback from a missing import.

### Shared math, different drawing

All geometry (`geometry.py` / `geometry.js`) is pure: no rendering dependencies, only math and stdlib. Engines consume `FrameState` objects and only differ in how they draw. This makes the engines easy to test independently of each other and easy to add new ones.

---

## The geometry contract (SPEC.md §3)

The view geometry specification in `SPEC.md §3` is normative. Any change to framing, camera placement, caption positioning, or easing must:

1. Update `SPEC.md §3`.
2. Update `geometry.py`.
3. Update `geometry.js`.
4. Update the shared fixture vectors in `tests/test_geometry.py` and the JS test equivalents.
5. Pass the cross-engine parity check.

---

## Testing

### Python tests

```bash
uv run pytest -q            # All ungated tests
uv run pytest -q -m blender # Blender engine tests (requires blender on PATH)
bash test.sh                # Full: lint + types + tests + functional renders
```

Test structure:

| File | What it tests |
|------|--------------|
| `tests/test_scene.py` | Pydantic model parsing, validation, load_scene |
| `tests/test_geometry.py` | Camera poses, frame plan, caption geometry, easing, opacity |
| `tests/test_images.py` | Pillow overlay compositing |
| `tests/test_juicy.py` | Color correction |
| `tests/test_engines.py` | Engine smoke tests (gated by pytest marks) |

Engine tests are marked with `@pytest.mark.blender`, `@pytest.mark.pygfx`, `@pytest.mark.playwright` and auto-skipped when the prerequisite is absent.

### JS tests

```bash
npm run test:unit     # node --test (scene, geometry, transition, scrollspy, stage)
npm run test:e2e      # Playwright: component mount, views, export, scrollspy
node verify/run.mjs   # Hard render gate in headless Chromium
python3 verify/gate.py  # PIL pixel variance assertion
```

### Cross-engine parity

The `verify_302.py` script renders `compact` and `expanded` stills of the `airbl-lores` test scene with every available engine and reports a cross-engine SSIM matrix. The acceptance threshold is SSIM ≥ 0.96 on the compact view (the expanded view has intentionally sparse framing and uses a lower threshold of std > 20).

---

## Adding a new engine

1. Create `src/vexy_stax/engines/myengine.py`.
2. Implement the `Engine` protocol (at minimum `render_image`; `render_video` can raise `NotImplementedError`).
3. Add a `name = "myengine"` class attribute.
4. Call `register(MyEngine())` at module level.
5. Add an availability probe to `_PROBES` in `base.py`.
6. Import the module in `_ensure_loaded()` in `base.py`.
7. Add `@pytest.mark.myengine` gate tests in `tests/test_engines.py`.

Engines receive `FrameState` objects from `geometry.frame_plan()` — consume them for per-frame camera, gaps, opacities, and caption opacities. Never reimplement the geometry formulas; always import from `geometry.py`.

---

## Versioning and releases

vexy-stax-py uses `hatch-vcs` with git tags for version numbers:

```toml
[tool.hatch.version]
source = "vcs"
fallback-version = "3.0.8"
```

Release workflow (CI):

```bash
bash publish.sh    # builds + publishes to PyPI via Trusted Publishing
```

The GitHub Actions release workflow handles PyPI upload with `id-token` permissions for Trusted Publishing (no stored API keys).

---

## Contributing

### Code style

- Python: ruff (lint + format), pyupgrade, autoflake. All enforced in CI.
- Type hints everywhere (`uv run mypy src/`).
- Docstrings on all public functions.

### Commit conventions

Follow the existing changelog format: one-line summary + reference to the issue number in parentheses. Example:

```
Fix pygfx caption plate render-order bleed-through (327.3)
```

### Making a geometry change

Geometry changes are high-risk — they affect all four renderers and the cross-engine parity tests. The safe procedure:

1. Update `SPEC.md §3` first (the spec is the source of truth).
2. Change `geometry.py` and `geometry.js` together.
3. Run `uv run pytest tests/test_geometry.py -v` to update expectations.
4. Run `node verify/run.mjs && python3 verify/gate.py` for the render gate.
5. Run the full cross-engine parity check.

### Scene format changes

The scene format is versioned. `version: 1` is the current version. Adding new optional fields with sensible defaults is backward-compatible. Removing fields or changing semantics requires a version bump and parser updates in both packages.

---

## License

- **vexy-stax-py**: MIT — Copyright 2026 Fontlab Ltd.
- **vexy-stax-js**: Apache-2.0 — Copyright 2026 Fontlab Ltd.
- **Bundled font** (`vexy-stax.ttf`, Zalando Sans): SIL Open Font License 1.1 (see `fonts/OFL.txt`)
