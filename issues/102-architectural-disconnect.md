---
this_file: issues/102-architectural-disconnect.md
priority: CRITICAL
category: Architecture
created: 2025-11-06
---

# Issue 102: Critical Architectural Disconnect Between Implementation and Intent

## Problem Statement

The codebase exhibits severe architectural split personality: the CLI exclusively uses Playwright browser automation while the entire renderer module infrastructure built for pygfx sits unused. This creates user confusion, dependency bloat, and blocks the stated project goal of headless rendering.

## Symptoms

### User Experience
1. User installs `vexy-stax` expecting headless renderer (per README tagline)
2. Runs `vexy-stax render --images scene.json --output out.png`
3. Gets error: "Cannot connect to http://localhost:5173"
4. Discovers they need to:
   - Install Playwright browsers (`playwright install chromium`)
   - Clone vexy-stax-js repository
   - Run Node.js dev server (`npm run dev`)
   - Only then can render work

**Expected**: Single command renders scene headlessly with pygfx
**Actual**: Complex multi-step setup requiring browser automation

### Code Evidence
- `src/vexy_stax/cli.py:113-153` - All CLI commands route through `VexyStaxBrowser`
- `src/vexy_stax/browser.py` - Entire Playwright automation layer still primary path
- `src/vexy_stax/renderer/` - Complete pygfx infrastructure unused by CLI
- `pyproject.toml:24-32` - Both `playwright>=1.40.0` AND `pygfx>=0.15.0` dependencies

### Test Coverage Illusion
- 53/53 tests passing
- **Zero tests actually render with pygfx**
- All renderer tests use stubs: `StubCanvas`, `StubRenderer`, fake textures
- PNG "export" writes to `.npy` files, never actual PNG rendering
- Video export untested with real codecs

## Root Causes

1. **Incremental Development Stall**: Renderer scaffolding added but CLI integration never completed
2. **Testing Anti-Pattern**: Dependency injection enables full stubbing, tests pass without real implementation
3. **Dual Implementation Maintenance**: Both Playwright and pygfx paths kept alive, neither deprecated
4. **Documentation Lag**: README promises pygfx pivot but shows Playwright examples
5. **Missing Integration Layer**: No bridge code connects loader → renderer → CLI

## Impact Assessment

### Critical (Blocks Primary Use Case)
- **Headless rendering non-functional**: Users can't render without browser
- **CI/CD pipeline broken**: Requires GUI environment for Chromium
- **Dependency waste**: 20+ packages from Playwright unused in target state

### High (Quality & Performance)
- **Output quality unknown**: No validation pygfx matches JS renderer
- **Performance uncharacterized**: No idea if it's faster/slower than browser
- **Resource usage mystery**: Memory, GPU requirements undocumented

### Medium (Developer Experience)
- **Contributor confusion**: Which path to improve?
- **Test suite misleading**: Green lights with zero real validation
- **Code rot risk**: Playwright code maintained but target for deletion

## Concrete Failures

### Test Command: `vexy-stax render --images test-img/layer123.json --output test.png`

**Without dev server running:**
```
RuntimeError: Cannot connect to http://localhost:5173/vexy-stax-js/
Make sure the dev server is running:
  cd vexy-stax-js && npm run dev
```

**With dev server running but headless server (no display):**
```
playwright._impl._errors.TargetClosedError: Target closed
===================================================== Most recent approach =====
  navigating to "http://localhost:5173/vexy-stax-js/", waiting until "load"
```

**Expected behavior:**
```bash
vexy-stax render --images scene.json --output render.png
# Loads JSON, renders with pygfx, writes PNG
✓ Rendered scene.json → render.png (2048x1536 @ 2x scale) in 0.8s
```

## Required Changes

### Phase 1: Establish Pygfx Path (Week 1)
1. Create `pygfx_render()` function in new `src/vexy_stax/render_pipeline.py`
2. Wire: loader → context → scene_builder → camera → export_png
3. Add **ONE** smoke test that actually renders with real pygfx/wgpu
4. Document GPU requirements and fallback behavior

### Phase 2: Integrate to CLI (Week 1-2)
1. Add `--backend` flag to `render` command: `playwright` (default) or `pygfx`
2. Route to appropriate implementation
3. Test both paths work
4. Update error messages for each backend

### Phase 3: Flip Default (Week 2)
1. Make `pygfx` default backend
2. Mark Playwright backend as deprecated with warning
3. Update all documentation and examples
4. Add migration guide

### Phase 4: Deprecation (Week 3-4)
1. Remove Playwright dependency from `requires`
2. Move to optional dependency group `[playwright]`
3. Remove Playwright CLI commands or gate behind feature flag
4. Clean up browser automation code

## Success Metrics

1. **Smoke test passes**: Real pygfx render produces valid PNG file
2. **CLI works headless**: `vexy-stax render` succeeds without browser/server
3. **CI/CD ready**: GitHub Actions can render on ubuntu-latest
4. **Quality validated**: Rendered PNG compared to JS reference within tolerance
5. **Docs updated**: README quick start shows pygfx path, Playwright marked legacy
6. **Dependency size reduced**: Package install 50% smaller without Playwright

## Risk Mitigation

### Risk: Pygfx doesn't work on user's hardware
- **Mitigation**: Add `vexy-stax doctor` command that tests GPU availability
- **Fallback**: Keep Playwright as emergency fallback temporarily

### Risk: Pygfx output quality insufficient
- **Mitigation**: Establish quality metrics early, iterate on materials/lighting
- **Acceptance**: Document known gaps, provide tuning options

### Risk: Breaking existing users
- **Mitigation**: Gradual deprecation with clear migration timeline
- **Communication**: CHANGELOG warnings, deprecation notices

## Related Issues

- Issues 103: Smoke test implementation
- Issues 104: GPU detection and fallbacks
- Issues 105: Quality validation framework
- Issues 106: Documentation overhaul

## References

- `PLAN.md` lines 26-29: "Replace stubs with real pygfx rendering"
- `WORK.md` line 24: "renderer pipeline still stub-driven for actual pygfx draws"
- `CHANGELOG.md` line 781: "renderer scaffolding" but no actual rendering
- CLI implementation: `src/vexy_stax/cli.py:113-153`
- Renderer modules: `src/vexy_stax/renderer/*.py`
