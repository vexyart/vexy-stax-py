---
this_file: issues/107-documentation-reality-mismatch.md
priority: HIGH
category: Documentation
created: 2025-11-06
---

# Issue 107: Documentation Describes Non-Existent Pygfx Workflow

## Problem Statement

README, QUICKSTART, and in-code documentation promise a pygfx-based headless renderer, but **actual implementation requires Playwright browser automation**. New users follow docs, hit errors, lose trust.

## Evidence of Mismatch

### README.md Claims (lines 1361-1366)
```markdown
# Vexy Stax PY

> Python toolkit pivoting toward a headless pygfx renderer for vexy-stax scenes
> (legacy Playwright automation remains until replacement lands).

## Why it exists
- Provide a pygfx-powered CLI that renders vexy-stax JSON scenes to high-quality
  PNG/MP4/MOV assets.
```

**User expectation**: Headless pygfx renderer is ready
**Reality**: Only Playwright works, pygfx not wired to CLI

### README Quick Start (lines 1369-1381)
```markdown
## Quick start
```bash
# 1. Install the package (editable install while hacking locally)
uv sync

# 2. Install Playwright browsers
uvx playwright install chromium

# 3. Create reference layers in ./test-img/
uv run vexy-stax-create-test

# 4. Launch the automation CLI (dev server must be running)
uv run vexy-stax launch --images test-img/
```
```

**Problem**: Step 2 implies Playwright is temporary, but it's the only working path

### Package Description (pyproject.toml:9)
```toml
description = "CLI tool for automating Vexy Stax 3D image visualization via Playwright"
```

**Inconsistent with README** which says "pygfx renderer"

### QUICKSTART.md Prerequisites (lines 1131-1140)
```markdown
## Prerequisites

Start the vexy-stax-js dev server first:

```bash
cd ../vexy-stax-js
npm install
npm run dev
# Server runs at http://localhost:5173/vexy-stax-js/
```
```

**User confusion**: *"I thought this was headless? Why do I need a dev server?"*

## User Journey Failures

### New User Scenario
1. **Finds package**: `pip search vexy-stax` or sees GitHub
2. **Reads README**: "pygfx-powered CLI", sounds perfect!
3. **Installs**: `pip install vexy-stax`
4. **Tries to render**: `vexy-stax render --images scene.json --output render.png`
5. **Gets error**: "Cannot connect to http://localhost:5173"
6. **Confusion**: Reads QUICKSTART, discovers need for:
   - Playwright browsers
   - Node.js
   - vexy-stax-js repo
   - Dev server running
7. **Frustration**: *"Why so complex? I just want to render!"*
8. **Abandons** or **files bug report**

### CI/CD Integration Scenario
Developer tries to use in GitHub Actions:
```yaml
- name: Render scenes
  run: vexy-stax render --images scene.json --output render.png
```

**Result**: Fails, no dev server
**Expected from docs**: Should work headlessly
**Reality**: Requires complex setup not documented for CI

## What Needs Updating

### 1. README.md Honesty Section
**Current**:
> Python toolkit pivoting toward a headless pygfx renderer

**Should be**:
```markdown
# Vexy Stax PY

Render vexy-stax 3D image scenes to PNG and video using Python.

## Current Status (v1.0.x)

**Browser Automation (Stable)**: Uses Playwright to control vexy-stax-js in Chromium
- ✅ Fully functional for PNG export and interactive preview
- ✅ Requires vexy-stax-js dev server and Chromium installation
- 📦 Complex setup but production-ready

**Pygfx Renderer (In Development)**: Native Python rendering without browser
- 🚧 Core modules implemented, CLI integration in progress
- 🚧 Not yet available via CLI commands
- 🎯 Target: v2.0 (headless, faster, simpler install)

**For now, use browser automation path**. See Quick Start below.
```

### 2. Installation Documentation
Split into two clear paths:

#### Path A: Browser Automation (Current - Works Now)
```markdown
### Browser Automation Setup (Current Stable)

**Prerequisites**:
- Python 3.12+
- Node.js 18+ (for vexy-stax-js dev server)
- Chromium (installed via Playwright)

**Installation**:
```bash
# Install Python package
pip install vexy-stax

# Install Playwright browsers
playwright install chromium

# Clone and run vexy-stax-js dev server
git clone https://github.com/vexyart/vexy-stax-js
cd vexy-stax-js
npm install
npm run dev
# Leave this running in terminal
```

**Usage**:
```bash
# In another terminal
vexy-stax render --images scene.json --output render.png
```

**Pros**: Proven, exact JS parity, interactive preview available
**Cons**: Complex setup, needs browser, requires dev server
```

#### Path B: Pygfx Renderer (Coming Soon)
```markdown
### Pygfx Renderer (v2.0 - In Development)

**Status**: Core implementation done, CLI wiring in progress

**When available**:
```bash
pip install vexy-stax>=2.0

# No browser, no dev server needed!
vexy-stax render --images scene.json --output render.png
```

**Progress tracking**: See PLAN.md and issues/102.md

**Want to help?** Contributions welcome on pygfx integration!
```

### 3. pyproject.toml Description
```toml
[project]
name = "vexy-stax"
description = "Render vexy-stax 3D image scenes to PNG/video (currently via Playwright, pygfx renderer coming in v2.0)"
```

### 4. CLI Help Text
```python
class VexyStaxCLI:
    """CLI for Vexy Stax rendering

    Current version uses Playwright browser automation.
    Requires vexy-stax-js dev server running on http://localhost:5173

    Native pygfx renderer coming in v2.0 (no browser needed).
    """

    def render(self, ...):
        """
        Render composition to PNG file (via Playwright)

        Prerequisites:
          - Playwright browsers: playwright install chromium
          - Dev server: cd vexy-stax-js && npm run dev

        Future: Will support native pygfx rendering (no browser).
        """
```

### 5. Error Messages with Context
```python
# In cli.py
except RuntimeError as e:
    if "Cannot connect to http://localhost:5173" in str(e):
        print(f"""
❌ Cannot connect to vexy-stax-js dev server

Current v1.x requires browser automation with dev server running.

Setup instructions:
  1. Clone vexy-stax-js: git clone https://github.com/vexyart/vexy-stax-js
  2. Install deps: cd vexy-stax-js && npm install
  3. Start server: npm run dev
  4. Leave running and retry this command

Alternative: Wait for v2.0 with native pygfx rendering (no server needed)
Or: Follow PLAN.md to help implement pygfx CLI integration

Docs: https://github.com/vexyart/vexy-stax-py#browser-automation-setup
        """)
        sys.exit(1)
```

### 6. CHANGELOG Clarity
```markdown
## [2.0.0] - TBD (Target)

### Added - Native Pygfx Rendering
- **Breaking**: Default backend changed from Playwright to pygfx
- Headless rendering without browser or dev server
- `--backend` flag to choose: `pygfx` (default) or `playwright` (legacy)
- Faster rendering, simpler installation

### Migration Guide
- Old: Required vexy-stax-js dev server running
- New: Just run `vexy-stax render` directly
- Fallback: Use `--backend=playwright` if pygfx issues

## [1.0.8] - Current

### Status
- Playwright browser automation (stable)
- Pygfx renderer modules implemented (not yet in CLI)
- See PLAN.md for pygfx integration roadmap
```

## Documentation Structure Overhaul

### Proposed Layout
```
docs/
  README.md                    # Landing page, clear current state
  QUICKSTART.md               # Working browser automation path
  QUICKSTART-PYGFX.md         # Future pygfx path (coming soon)
  INSTALLATION.md             # Detailed per-platform setup
    ├─ macos.md
    ├─ linux.md
    ├─ windows.md
    └─ docker.md
  TROUBLESHOOTING.md          # Common errors and solutions
  API.md                      # Python API (VexyStaxBrowser)
  DEVELOPMENT.md              # Contributing, pygfx integration
  MIGRATION-2.0.md            # For v2.0 release
```

### README.md Sections
1. **What is it** - One sentence purpose
2. **Current Status** - Browser automation works, pygfx coming
3. **Quick Start** - Working path only, link to detailed docs
4. **Why It Exists** - Use cases
5. **Roadmap** - Clear v1.x vs v2.0 plans
6. **Contributing** - How to help with pygfx
7. **Support** - Where to get help

## Examples Need Status Tags

### In README
```markdown
## Commands

### `vexy-stax render` [STABLE - Browser]
Render scene to PNG using Playwright automation.
Requires dev server running.

### `vexy-stax animate` [STUB - In Development]
Render animation to video.
Currently prints TODO message.

### `vexy-stax doctor` [PLANNED - v2.0]
Check GPU and rendering capabilities.
Will be available with pygfx integration.
```

## Success Criteria

1. ✅ New user follows README, successfully renders (no confusion)
2. ✅ Status of each feature clearly documented
3. ✅ No promises of features that don't exist
4. ✅ Clear migration path explained for v2.0
5. ✅ Error messages guide users to working setup
6. ✅ CI/CD examples actually work
7. ✅ Every command's status visible in `--help`

## Implementation Checklist

- [ ] Update README.md with status section
- [ ] Rewrite QUICKSTART.md for browser path
- [ ] Create QUICKSTART-PYGFX.md (coming soon)
- [ ] Add status tags to all commands in docs
- [ ] Update pyproject.toml description
- [ ] Enhance error messages with setup instructions
- [ ] Add TROUBLESHOOTING.md
- [ ] Create INSTALLATION.md with per-platform guides
- [ ] Update CLI --help text
- [ ] Review all docstrings for accuracy
- [ ] Add "Current Status" badge to README

## Related Issues

- Issue 102: Architectural disconnect (docs promise what code doesn't deliver)
- Issue 103: Smoke tests (docs should reflect tested reality)
- Issue 104: GPU strategy (docs should cover GPU requirements)

## Priority Justification

**HIGH** because:
- Directly affects user experience and trust
- Causes support burden (confused users filing issues)
- Quick fix (just writing, no code changes)
- High impact (prevents user frustration)
- Prerequisite for good open source reputation
