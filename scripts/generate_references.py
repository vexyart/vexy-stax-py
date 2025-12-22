#!/usr/bin/env -S uv run
# /// script
# dependencies = ["playwright"]
# ///
# this_file: scripts/generate_references.py
"""Generate reference images from JS renderer for visual regression tests.

Usage:
    1. Start the dev server: cd vexy-stax-js && npm run dev
    2. Run this script: python scripts/generate_references.py

The script renders scenes using Playwright (JS renderer) and saves them
to tests/fixtures/references/ for use in visual regression tests.

NOTE: JS canvas size is fixed (960×540 at scale=1). The reference images
use this native resolution; Python tests must render at matching size.
"""

from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vexy_stax.browser import VexyStaxBrowser


FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "references"

# Scenes to render - uses JS native canvas size (960×540 at scale=1)
SCENES = [
    {
        "json": Path(__file__).parent.parent.parent
        / "test-data"
        / "slides"
        / "slides_scene.json",
        "output": "slides_scene.png",
    },
    {
        "json": Path(__file__).parent.parent / "test-img" / "layer123.json",
        "output": "layer123.png",
    },
]


def main():
    """Generate all reference images."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating reference images from JS renderer...")
    print("Make sure vexy-stax-js dev server is running on http://localhost:5173")
    print()

    browser = VexyStaxBrowser(headless=True)

    try:
        browser.launch()
        print("✓ Browser launched")

        for scene in SCENES:
            json_path = scene["json"]
            output_path = FIXTURES_DIR / scene["output"]

            if not json_path.exists():
                print(f"⚠ Skipping {json_path.name}: file not found")
                continue

            print(f"  Rendering {json_path.name}...")

            # Load the scene
            browser.load_config(str(json_path))

            # Give time for render
            browser.page.wait_for_timeout(500)

            # Export PNG at native scale
            browser.export_png(scale=1, output_path=str(output_path))

            print(f"  ✓ Saved {output_path.name}")

    except RuntimeError as e:
        print(f"\n✗ Error: {e}")
        print("\nTo generate references:")
        print("  1. cd vexy-stax-js && npm run dev")
        print("  2. python scripts/generate_references.py")
        sys.exit(1)

    finally:
        browser.close()

    print()
    print(f"✓ Reference images saved to {FIXTURES_DIR}")
    print("  Run 'pytest tests/test_visual_regression.py' to compare pygfx renders")


if __name__ == "__main__":
    main()
