# Architecture and contributing

## Repository layout

```text
vexy-stax-py/
├── src/vexy_stax/
│   ├── __init__.py          # __version__ (from the hatch-vcs _version.py)
│   ├── __main__.py          # python -m vexy_stax
│   ├── cli.py               # Fire + Rich CLI (class Stax)
│   ├── scene.py             # Pydantic v2 scene model, load_scene()
│   ├── geometry.py          # pure view math (cameras, gaps, captions, frame plans)
│   ├── images.py            # Pillow image reading and flat overlay
│   ├── juicy.py             # per-channel colour matching
│   ├── showcase.py          # showcase / benchmark runner used by example.py
│   ├── engines/
│   │   ├── base.py          # Engine protocol, registry, availability probes
│   │   ├── pygfx.py         # off-screen WGPU renderer
│   │   ├── blender.py       # Blender job builder and subprocess runner
│   │   ├── _blender_render.py  # runs inside Blender's own Python (imports bpy)
│   │   └── playwright.py    # headless Chromium + vexy-stax-js renderer
│   └── fonts/               # vexy-stax.ttf + OFL.txt
├── schema/                  # JSON Schema and an example scene
├── testdata/                # airbl, airbl-lores, airbl-orig sample decks + scenes
├── tests/                   # pytest suite
├── src_docs/                # this documentation (ProperDocs + MaterialX)
├── docs/                    # built site served by GitHub Pages (generated)
├── SPEC.md                  # normative scene format and geometry specification
├── example.py               # renders the showcase with every available engine
├── verify_302.py            # cross-engine comparison of showcase output
├── build.sh, publish.sh, install.sh
└── pyproject.toml
```

## Design principles

**Parse, don't validate.** The scene is parsed once, at the boundary, into Pydantic models with `extra="forbid"`. If `load_scene()` returns, the scene is valid; the rest of the code does not re-check fields.

**Shared math, separate drawing.** `geometry.py` holds every formula for camera placement, spacing, opacity and caption layout. Engines only draw the poses and per-frame values it produces. vexy-stax-js mirrors the same module in `geometry.js`, so a geometry change must land in both.

**Cheap engine discovery.** `engines/base.py` probes engines without importing them (`shutil.which`, `importlib.util.find_spec`) and imports the engine modules only when the registry is first used.

**Fail loudly.** Unknown scene fields, unknown engines, missing transitions, a missing ffmpeg or a missing JS bundle all raise errors that name the cause and, where possible, the fix.

## Changing the geometry

Geometry changes affect every renderer. Work in this order:

1. Update `SPEC.md` section 3, which is the source of truth.
2. Change `src/vexy_stax/geometry.py` and `vexy-stax-js/src/geometry.js` together.
3. Update the expectations in `tests/test_geometry.py` and the JS tests.
4. Run `python example.py` to render the showcase with every available engine, then `uv run -s verify_302.py` to compare the engines' output.

## Changing the scene format

The format is versioned (`"version": 1`). Adding an optional field with a default that keeps the old behaviour is backward compatible. Update `scene.py`, the JSON Schema in `schema/`, and the JS parser together. Removing a field or changing its meaning needs a version bump.

## Tests

```bash
uv run pytest -q                 # default selection: everything except "slow"
uv run pytest -q -m slow         # long video renders
uv run pytest -q -m blender      # only the Blender tests
```

| File | Covers |
|------|--------|
| `tests/test_scene.py` | model parsing, defaults, rejection of unknown fields, `load_scene()` |
| `tests/test_geometry.py` | cameras, gaps, frame plans, captions, easing, opacity |
| `tests/test_cli.py` | `dir2scene` output, sorting, flags, captions, errors |
| `tests/test_images.py` | Pillow overlay |
| `tests/test_juicy.py` | colour correction |
| `tests/test_pygfx.py`, `tests/test_blender.py`, `tests/test_playwright.py` | engine renders |

The markers `blender`, `pygfx`, `playwright` and `slow` are declared in `pyproject.toml`. Engine tests skip themselves when the engine is unavailable. Tests use the sample deck in `testdata/airbl-lores/` (nine layers, 1247 × 806), so they run without network access.

## Code style

- Ruff for linting and formatting (`line-length = 120`, target Python 3.12, rules `E`, `F`, `I`, `UP`).
- Type hints throughout; `mypy` is configured in `pyproject.toml`. `_blender_render.py` is excluded because it imports `bpy`, which only exists inside Blender.
- Every source file carries a `this_file:` comment with its path.

## Building

`./build.sh` in the repository root builds everything:

```bash
./build.sh            # lint + tests, docs, package
./build.sh test       # ruff check --fix, ruff format, pytest
./build.sh docs       # src_docs/build.sh → docs/
./build.sh package    # uv build into dist/, then twine check
```

The documentation alone can be built or previewed with:

```bash
src_docs/build.sh          # strict build into docs/
src_docs/build.sh serve    # live preview on http://127.0.0.1:8000
```

## Versions and releases

The version comes from git tags through hatch-vcs (`[tool.hatch.version] source = "vcs"`), which writes `src/vexy_stax/_version.py` at build time. That file is ignored by git.

`./publish.sh` makes a release:

1. `uvx gitnextver` commits pending changes, tags the next `vX.Y.Z` and pushes.
2. The script checks that `HEAD` carries a `vX.Y.Z` tag and stops if not.
3. `./build.sh package` builds the sdist and wheel and checks them with twine.
4. `uv publish` uploads them. It needs `UV_PUBLISH_TOKEN` or another uv publish credential.

Pushing the tag also starts the `Release` GitHub workflow, which builds the package and uploads it with PyPI trusted publishing (`skip-existing`, so a version already uploaded by `publish.sh` doesn't fail it) and creates a GitHub release with the built files.

## Documentation

The documentation sources are in `src_docs/md/`, configured by `src_docs/mkdocs.yml`. The `Docs` workflow rebuilds `docs/` on every push to `main` that touches `src_docs/`, and GitHub Pages serves `docs/` at <https://vexy.dev/vexy-stax-py/>. Edit the Markdown in `src_docs/md/`, never the generated HTML in `docs/`.
