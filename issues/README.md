---
this_file: issues/README.md
---

# Vexy Stax PY - Issues & Action Items

## Issue Summary

This folder contains detailed documentation of all identified problems, doubts, and improvement opportunities discovered through comprehensive codebase analysis and user perspective thinking.

## Critical Issues (Blocking)

### Issue 102: Architectural Disconnect
**Status**: CRITICAL - Blocks primary use case
**Problem**: CLI only uses Playwright; pygfx renderer modules sit unused
**Impact**: Users cannot use headless rendering; defeats project purpose
**Priority**: Must fix first - prerequisite for everything else

### Issue 103: No Smoke Test
**Status**: CRITICAL - False test confidence
**Problem**: All 53 tests pass using stubs; zero actual GPU rendering validated
**Impact**: Could ship completely broken renderer with passing tests
**Priority**: Must validate rendering actually works before proceeding

## High Priority Issues

### Issue 104: GPU Strategy Missing
**Status**: HIGH - Blocks deployment
**Problem**: No GPU detection, fallbacks, or user guidance
**Impact**: Fails in CI/CD, Docker, headless servers; cryptic errors
**Priority**: Required for production deployment and documentation

### Issue 105: Quality Validation Missing
**Status**: HIGH - No confidence in output
**Problem**: Cannot verify pygfx output matches JS reference quality
**Impact**: No assurance of rendering fidelity; no regression detection
**Priority**: Core value proposition is parity with JS

### Issue 107: Documentation Reality Mismatch
**Status**: HIGH - User confusion and trust loss
**Problem**: README promises pygfx but only Playwright works
**Impact**: New users frustrated, abandon project, trust damaged
**Priority**: Quick fix with high impact on user experience

## Medium Priority Issues

### Issue 106: Video Export Unimplemented
**Status**: MEDIUM - Feature incomplete
**Problem**: `animate` command prints "TODO"; video encoding stubbed
**Impact**: Core goal from issues/101.md not delivered
**Priority**: Important but still images work; can iterate

### Issue 108: User Experience & Errors
**Status**: MEDIUM - UX polish needed
**Problem**: Cryptic errors, no validation, poor feedback
**Impact**: Frustrating user experience, support burden
**Priority**: Incremental improvements; workarounds exist

## Issue Relationships

```
Issue 102 (Architectural Disconnect)
    └─ Blocks → Issue 103 (Smoke Test)
        └─ Enables → Issue 105 (Quality Validation)
            └─ Enables → Issue 106 (Video Export)

Issue 104 (GPU Strategy)
    └─ Required by → Issue 103 (Smoke Test)
    └─ Required by → All production deployment

Issue 107 (Documentation)
    └─ Can proceed in parallel
    └─ Quick fix, high impact

Issue 108 (UX/Errors)
    └─ Can proceed in parallel
    └─ Incremental improvements
```

## Critical Path

**Phase 1**: Make ONE path work
1. Implement smoke test (Issue 103)
2. Wire pygfx to CLI (Issue 102)
3. Update documentation (Issue 107)

**Phase 2**: Make it deployable
4. GPU detection/fallbacks (Issue 104)
5. Quality validation (Issue 105)

**Phase 3**: Complete features
6. Video export (Issue 106)
7. UX improvements (Issue 108)

## How to Use This Documentation

### For Contributors
1. Read issue files to understand problems deeply
2. Check TODO.md for specific actionable tasks
3. Refer to PLAN.md for overall strategy
4. Update WORK.md as you make progress
5. Document solutions in CHANGELOG.md

### For Project Maintainers
1. Issues prioritize work (CRITICAL → HIGH → MEDIUM)
2. Each issue has success criteria for completion
3. Related issues show dependencies
4. Priority justifications explain urgency

### For Users
1. Issue 107 explains documentation problems
2. Issue 104 helps troubleshoot GPU issues
3. Issue 108 lists known UX pain points
4. All issues link to relevant code locations

## Issue Template

Each issue document contains:
- **Problem Statement**: What's wrong and why it matters
- **Evidence**: Code snippets, user scenarios, test results
- **Impact Assessment**: Who's affected and how severely
- **Root Causes**: Why the problem exists
- **Concrete Failures**: Reproducible examples
- **Required Changes**: Specific implementation steps
- **Success Criteria**: How to know when it's fixed
- **Priority Justification**: Why this urgency level
- **Related Issues**: Dependencies and connections

## Next Steps

1. **Immediate**: Start with Issue 102 + 103 (smoke test + integration)
2. **Week 1**: Add Issue 107 (documentation honesty)
3. **Week 2**: Address Issue 104 (GPU strategy)
4. **Week 3+**: Continue with remaining issues

## Questions?

- Check TODO.md for specific tasks
- Check PLAN.md for strategy
- Check WORK.md for current progress
- Check issue files for detailed analysis

---

**Last Updated**: 2025-11-06
**Total Issues**: 7 (2 Critical, 3 High, 2 Medium)
**Analysis Date**: Based on codebase state as of 2025-11-06
