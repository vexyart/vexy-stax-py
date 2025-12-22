#!/bin/bash
# this_file: vexy-stax-py/build.sh
# Build script for vexy-stax-py

cd "$(dirname "$0")"

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Building vexy-stax-py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if uv is installed (required)
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "   Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv $(uv --version | head -n1)"
echo

# Sync dependencies
echo "📦 Syncing dependencies..."
uv sync --quiet
echo

# Run tests
echo "🧪 Running tests..."
uv run pytest -v || {
    echo
    echo "⚠️  Tests failed, but continuing with build..."
    echo
}

# Build package
echo "🔨 Building package..."
uv build

echo

# Verify output
if [ ! -d "dist" ]; then
    echo "❌ Error: dist/ directory not created"
    exit 1
fi

# Count artifacts
WHEEL_COUNT=$(find dist -name "*.whl" | wc -l | tr -d ' ')
SDIST_COUNT=$(find dist -name "*.tar.gz" | wc -l | tr -d ' ')

if [ "$WHEEL_COUNT" -eq 0 ] && [ "$SDIST_COUNT" -eq 0 ]; then
    echo "❌ Error: No build artifacts found in dist/"
    exit 1
fi

# Show build stats
DIST_SIZE=$(du -sh dist/ | cut -f1)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Build complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Output:  dist/"
echo "  Size:    $DIST_SIZE"
echo "  Wheels:  $WHEEL_COUNT"
echo "  SDist:   $SDIST_COUNT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "To install locally:"
echo "  pip install dist/*.whl"
echo
echo "To publish to PyPI:"
echo "  # Create git tag first:"
echo "  git tag v0.1.0"
echo "  git push origin v0.1.0"
echo "  # GitHub Actions will auto-publish"
echo
echo "Note: Python package has no web UI. Use vexy-stax-js for the web app."
echo
