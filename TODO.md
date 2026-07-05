<!-- this_file: TODO.md -->

# TODO

Bigger ideas deferred from the modernization pass. None are blockers; the package
ships clean today (ruff + mypy clean, 85 tests green).

## Docs

- [ ] Consider a ProperDocs + MaterialX (`src_docs/md/` + `src_docs/mkdocs.yaml`
      compiling into `docs/`) build to match the richer sibling docs, if the flat
      12-chapter just-the-docs Jekyll site ever outgrows itself. The current
      Jekyll site is complete and correct, so this is optional polish.
- [ ] Add a dedicated `scene-format.md` cross-reference table that diffs the Python
      and JS scene-schema versions, so the two stay provably in sync with `SPEC.md`.

## Packaging

- [ ] Split the heavy render backends behind `extras_require` (e.g.
      `vexy-stax[pygfx]`, `vexy-stax[blender]`, `vexy-stax[playwright]`) so users
      who only need `overlay`/`dir2scene` don't pull `pygfx`, `opencv`, and
      `playwright`. Keep a sensible default extra for the common case.

## CI

- [ ] Add `uv run mypy src` as a non-blocking (or blocking, once stable) CI step —
      the config is now clean, so this only needs wiring into `ci.yml`.
- [ ] Add a Python 3.13 leg to the CI matrix once the GPU/`pygfx` stack supports it
      on the runner.

## Tests

- [ ] Add an explicit parity test that loads a shared fixture scene and asserts the
      Python `geometry.py` outputs match the JS `geometry.js` fixture vectors
      byte-for-byte (today each side tests its own copy of the vectors).
