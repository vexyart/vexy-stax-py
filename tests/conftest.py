# this_file: tests/conftest.py
"""Shared test fixtures.

Uses the repo-local ``testdata/airbl-lores`` slides (8 layers, 1246x806) so the
unit tests run fully standalone.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTDATA_DIR = PROJECT_ROOT / "testdata" / "airbl-lores"

LAYER_FILES = [
    "airbl-020-source.png",
    "airbl-030-pink.png",
    "airbl-040-stars.png",
    "airbl-050-backdrop.png",
    "airbl-060-outline.png",
    "airbl-070-inline.png",
    "airbl-080-halftone.png",
    "airbl-090-ui.png",
]

# Native dimensions of every airbl-lores layer.
LAYER_WIDTH = 1246
LAYER_HEIGHT = 806


@pytest.fixture
def image_paths() -> list[str]:
    """Return absolute paths to all airbl-lores test layer images."""
    paths = [str(TESTDATA_DIR / f) for f in LAYER_FILES]
    for p in paths:
        if not os.path.isfile(p):
            pytest.skip(f"Test image not found: {p}")
    return paths


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Return a temporary output directory."""
    return tmp_path
