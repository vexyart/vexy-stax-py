#!/usr/bin/env python3
# this_file: example.py
# Thin wrapper (issue 335 §1): the showcase/benchmark logic now lives in
# vexy_stax.showcase.run_showcase. This renders a compact still, an expanded still and a short
# held-still + transition video of testdata/airbl.scene.json with every available engine into
# outputs/<engine>/. Unavailable engines are skipped (not fatal); stills are verified non-blank.

import sys
from pathlib import Path

from vexy_stax.showcase import run_showcase


def main() -> None:
    ok = run_showcase(project_dir=Path(__file__).resolve().parent)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
