#!/usr/bin/env bash
# this_file: build.sh
# Build the documentation (docs/) and the Python package (dist/).
# Usage: ./build.sh [all|test|docs|package]   (default: all)
#   test    — ruff check --fix + ruff format + pytest (default selection excludes 'slow')
#   docs    — src_docs/build.sh (strict ProperDocs build into docs/)
#   package — clean dist/, uv build (wheel + sdist), twine check
#   all     — test, docs, package
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
target="${1:-all}"
case "$target" in
  all|test|docs|package) ;;
  *) echo "usage: $0 [all|test|docs|package]" >&2; exit 2 ;;
esac
if [[ "$target" == all || "$target" == test ]]; then
  uvx ruff check --fix src tests
  uvx ruff format src tests
  uv run pytest -q
fi
if [[ "$target" == all || "$target" == docs ]]; then
  src_docs/build.sh
fi
if [[ "$target" == all || "$target" == package ]]; then
  # Clean first so publish never sees a stale build (e.g. a dev-version wheel).
  rm -rf dist
  uv build
  uvx twine check dist/*
fi
