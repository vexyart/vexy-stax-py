#!/bin/bash
# this_file: vexy-stax-py/run.sh
# Quick runner for development - sets PYTHONPATH

set -e

export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Vexy Stax PY - Development Runner"
echo "  PYTHONPATH: $PYTHONPATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $# -eq 0 ]; then
    echo "Usage:"
    echo "  ./run.sh python -m vexy_stax.create_test_images"
    echo "  ./run.sh python -m vexy_stax.cli launch --images=test-img/"
    echo "  ./run.sh python -m vexy_stax.cli animate --images=test-img/layer123.json"
    exit 0
fi

"$@"
