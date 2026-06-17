<!-- this_file: CHANGELOG.md -->

# Changelog

All notable changes to this project are documented here.

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
    tests for `juicy.py`/`images.py` ported from `vexy-stax2-py` and adapted to
    the repo-local `airbl-lores` fixtures (8 layers, 1246x806).

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
    `blender`/`pygfx`/`playwright` stub engines (raise `NotImplementedError`).
  - `images.py`, `juicy.py` — copied verbatim from `vexy-stax2-py`.
  - `cli.py` — fire + rich CLI: `render`, `video`, `overlay`, `engines`.
  - `tests/` — scene and geometry unit tests with shared fixture vectors.
