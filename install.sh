#!/usr/bin/env bash
# install.sh - Install vexy-stax-py in editable mode
# Vexy Stax Py: Headless 3D renderer for layered image stacks with depth effects (pygfx + Playwright).
# Part of Vexy Stax, a creative 3D image stacking tool.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing vexy-stax-py in editable mode..."
uv pip install --system -e .

echo "==> Install complete."
