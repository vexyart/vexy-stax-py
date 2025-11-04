#!/bin/bash
# this_file: vexy-stax-py/dev.sh
# Development environment setup for vexy-stax-py

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setting up vexy-stax-py development"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python $(python3 --version)"
echo

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
    echo
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install in editable mode
echo "📦 Installing package in editable mode..."
if command -v uv &> /dev/null; then
    uv pip install -e ".[dev]"
else
    pip install -e ".[dev]"
fi

echo

# Check if Playwright browsers are installed (future)
# if command -v playwright &> /dev/null; then
#     echo "🌐 Installing Playwright browsers..."
#     playwright install chromium
#     echo
# fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Development environment ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Virtual environment activated. Available commands:"
echo
echo "  # Generate test images"
echo "  vexy-stax-create-test"
echo
echo "  # Run tests"
echo "  pytest -v"
echo
echo "  # Deactivate when done"
echo "  deactivate"
echo
