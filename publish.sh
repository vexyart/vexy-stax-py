#!/usr/bin/env bash
# this_file: publish.sh
# Publish vexy-stax to PyPI. PUBLISHES BY DEFAULT.
# Pass --dryrun (or --dry-run) to build + validate without uploading.
# Workflow: build (clean) → guard against dev versions → publish (retry-on-429).
set -euo pipefail
cd "$(dirname "$0")"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

DRYRUN=0
for arg in "$@"; do
    case "$arg" in
        --dryrun|--dry-run) DRYRUN=1 ;;
        *) echo "Unknown argument: $arg (only --dryrun is supported)" >&2; exit 2 ;;
    esac
done

# Robust uv publish with exponential backoff on transient PyPI errors (429 etc).
publish_to_pypi() {
    local max_attempts="${PYPI_PUBLISH_MAX_ATTEMPTS:-6}"
    local delay="${PYPI_PUBLISH_INITIAL_DELAY:-300}"
    local max_delay="${PYPI_PUBLISH_MAX_DELAY:-3600}"
    local attempt=1
    local status=0
    local retry_pattern="429|Too Many Requests|too many new projects created|timeout|timed out|temporarily unavailable|502|503|504|connection reset|network"
    local log_file
    local errexit_was_set=0

    case $- in
        *e*) errexit_was_set=1 ;;
    esac

    log_file="$(mktemp "${TMPDIR:-/tmp}/uv-publish.XXXXXX")"

    while [ "$attempt" -le "$max_attempts" ]; do
        : > "$log_file"
        set +e
        uv publish "$@" 2>&1 | tee "$log_file"
        status=${PIPESTATUS[0]}
        if [ "$errexit_was_set" -eq 1 ]; then
            set -e
        else
            set +e
        fi

        if [ "$status" -eq 0 ]; then
            rm -f "$log_file"
            return 0
        fi

        if ! grep -Eiq "$retry_pattern" "$log_file"; then
            echo "PyPI publish failed with a non-retryable error. Not retrying."
            rm -f "$log_file"
            return "$status"
        fi

        if [ "$attempt" -ge "$max_attempts" ]; then
            echo "PyPI publish still failed after $max_attempts attempts."
            echo "If this is PyPI new-project rate limiting, wait for the quota window to reset before rerunning."
            rm -f "$log_file"
            return "$status"
        fi

        local jitter=$((RANDOM % 31))
        local sleep_for=$((delay + jitter))

        if grep -Eiq "too many new projects created" "$log_file"; then
            echo "PyPI is rate-limiting new project creation. This can require a long wait; retrying with backoff."
        fi

        echo "Retrying PyPI publish in ${sleep_for}s (attempt $((attempt + 1))/$max_attempts)..."
        sleep "$sleep_for"

        attempt=$((attempt + 1))
        delay=$((delay * 2))
        if [ "$delay" -gt "$max_delay" ]; then
            delay="$max_delay"
        fi
    done

    rm -f "$log_file"
    return "$status"
}

echo -e "${BLUE}Publishing vexy-stax...${NC}"

# Step 1: clean build (lint + test + wheel/sdist). build.sh wipes dist/ first.
echo -e "${YELLOW}→ Building...${NC}"
./build.sh

if [ ! -d "dist" ] || [ -z "$(ls -A dist 2>/dev/null)" ]; then
    echo -e "${RED}❌ No distribution files found in dist/${NC}"
    exit 1
fi

# Step 2: refuse to publish a dev/local version (PyPI rejects '+local' identifiers,
# and you almost never mean to ship uncommitted work). hatch-vcs emits these when
# the tree is dirty or HEAD is past the version tag.
if ls dist/* | grep -Eq 'dev[0-9]|\+g[0-9a-f]'; then
    echo -e "${RED}❌ Built a dev/local version (see dist/). Refusing to publish.${NC}"
    echo -e "   Commit your changes and tag the release (e.g. 'git tag v3.0.0') on a clean tree, then retry."
    exit 1
fi

# Step 3: publish (or validate only).
if [ "$DRYRUN" -eq 1 ]; then
    echo -e "${YELLOW}→ DRY RUN (--dryrun). Nothing will be uploaded. Artifacts:${NC}"
    for f in dist/*; do
        echo -e "    ${BLUE}•${NC} $f ($(du -h "$f" | cut -f1))"
    done
    if uv publish --help 2>&1 | grep -q -- '--dry-run'; then
        echo -e "${YELLOW}→ Validating with 'uv publish --dry-run' (no upload)...${NC}"
        uv publish --dry-run dist/* \
            || echo -e "  ${YELLOW}(dry-run precheck reported an issue — review above)${NC}"
    fi
    echo -e "${GREEN}✅ Dry run complete. Nothing published.${NC}"
else
    echo -e "${YELLOW}→ Publishing to PyPI...${NC}"
    publish_to_pypi dist/*
    echo -e "${GREEN}✅ Package published successfully${NC}"
fi
