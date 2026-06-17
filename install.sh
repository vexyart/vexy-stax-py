#!/usr/bin/env bash
# this_file: install.sh
# Install vexy-stax (offline Python package) into a fresh venv + Chromium for playwright.
set -euo pipefail
cd "$(dirname "$0")"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Installing vexy-stax...${NC}"

# Step 1: fresh, reproducible venv (idempotent: --clear rebuilds it each run).
echo -e "${YELLOW}→ Creating venv (.venv, Python 3.12)...${NC}"
uv venv --python 3.12 --clear

# Step 2: sync locked dependencies into the venv.
echo -e "${YELLOW}→ Syncing dependencies (uv sync)...${NC}"
uv sync

# Step 3: Chromium for the playwright engine/tests.
echo -e "${YELLOW}→ Installing Chromium for Playwright...${NC}"
uv run playwright install chromium

# Step 4: note + check system deps that pip can't provide.
echo -e "${YELLOW}→ Checking system dependencies...${NC}"
echo -e "  ${BLUE}note:${NC} the blender engine needs Blender (brew install --cask blender);"
echo -e "  ${BLUE}note:${NC} video output needs ffmpeg (brew install ffmpeg)."
missing=""
for dep in blender ffmpeg; do
    if command -v "$dep" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✔${NC} $dep found: $(command -v "$dep")"
    else
        echo -e "  ${RED}✘${NC} $dep NOT found (that engine/feature will be skipped)"
        missing="$missing $dep"
    fi
done
if [ -n "$missing" ]; then
    echo -e "${YELLOW}⚠ Missing system deps:${missing} — install them for full functionality.${NC}"
fi

echo -e "${GREEN}✅ Install complete.${NC}"
