#!/bin/bash
# this_file: vexy-stax-py/build.sh
# Build script for vexy-stax-py

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Building vexy-stax-py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Install from: https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✓ $PYTHON_VERSION"

# Check if uv is installed (recommended)
if command -v uv &> /dev/null; then
    echo "✓ uv $(uv --version | head -n1)"
    BUILD_CMD="uv build"
    echo
else
    echo "⚠️  uv not found (using pip instead)"
    echo "   Install uv for faster builds: curl -LsSf https://astral.sh/uv/install.sh | sh"
    BUILD_CMD="python3 -m build"
    echo

    # Check if build module is installed
    if ! python3 -c "import build" 2>/dev/null; then
        echo "📦 Installing build module..."
        python3 -m pip install --upgrade build
        echo
    fi
fi

# Run tests first (if pytest is available)
if python3 -c "import pytest" 2>/dev/null; then
    echo "🧪 Running tests..."
    python3 -m pytest -v || {
        echo
        echo "⚠️  Tests failed, but continuing with build..."
        echo
    }
else
    echo "⚠️  pytest not found, skipping tests"
    echo
fi

# Build package
echo "🔨 Building package..."
$BUILD_CMD

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
