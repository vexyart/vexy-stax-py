#!/usr/bin/env bash
# this_file: build.sh
# Build vexy-stax: lint → test → build wheel+sdist. Fails on any error.
set -euo pipefail
cd "$(dirname "$0")"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Building vexy-stax...${NC}"

# Step 1: lint + format.
echo -e "${YELLOW}→ Linting (ruff check --fix)...${NC}"
uvx ruff check --fix src tests
echo -e "${YELLOW}→ Formatting (ruff format)...${NC}"
uvx ruff format src tests

# Step 2: tests (default selection excludes 'slow' video renders).
echo -e "${YELLOW}→ Running tests...${NC}"
uv run pytest -q

# Step 3: build wheel + sdist into dist/. Clean first so publish never sees a
# stale build (e.g. a prior dev-version wheel PyPI would reject as a local version).
echo -e "${YELLOW}→ Building wheel + sdist (uv build)...${NC}"
rm -rf dist
uv build

echo -e "${GREEN}✅ Build completed successfully${NC}"
ls -la dist/
