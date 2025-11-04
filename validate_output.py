#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pillow"]
# ///
# this_file: validate_output.py
"""
Output validation script for all vexy-stax projects.
Validates that generated PNG files are valid and have expected dimensions.
"""

from pathlib import Path
from PIL import Image


def validate_png(
    path: Path, expected_width: int | None = None, expected_height: int | None = None
) -> tuple[bool, str]:
    """
    Validate a PNG file.

    Args:
        path: Path to PNG file
        expected_width: Expected width in pixels (None to skip check)
        expected_height: Expected height in pixels (None to skip check)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path.exists():
        return False, f"File not found: {path}"

    try:
        with Image.open(path) as img:
            # Check format
            if img.format != "PNG":
                return False, f"File is not PNG format (got: {img.format})"

            # Check dimensions if specified
            if expected_width and img.width != expected_width:
                return (
                    False,
                    f"Width mismatch: expected {expected_width}px, got {img.width}px",
                )

            if expected_height and img.height != expected_height:
                return (
                    False,
                    f"Height mismatch: expected {expected_height}px, got {img.height}px",
                )

            # Check if image has content (not all zeros)
            if img.mode in ("RGB", "RGBA"):
                data = list(img.getdata())
                if all(
                    pixel == (0, 0, 0) or pixel == (0, 0, 0, 0) for pixel in data[:100]
                ):  # Check first 100 pixels
                    return False, "Image appears to be blank (all black pixels)"

            return True, ""

    except Exception as e:
        return False, f"Failed to validate PNG: {e}"


def main():
    """Validate all output PNGs."""
    base_dir = Path(__file__).parent
    outputs = {
        "vexy-stax-pc": (base_dir / "img/out-pc.png", 800, 600),
        "vexy-stax-pm": (base_dir / "img/out-pm.png", 800, 600),
        "vexy-stax-wl": (base_dir / "img/out-wl.png", 800, 600),
        "vexy-stax-wt": (base_dir / "img/out-wt.png", 800, 600),
    }

    all_valid = True
    print("Validating output PNG files...\n")

    for project, (path, width, height) in outputs.items():
        valid, error = validate_png(path, width, height)
        status = "✓" if valid else "✗"
        print(f"{status} {project}: {path.name}")

        if valid:
            with Image.open(path) as img:
                print(
                    f"  Size: {img.width}x{img.height}, Mode: {img.mode}, Size: {path.stat().st_size} bytes"
                )
        else:
            print(f"  Error: {error}")
            all_valid = False
        print()

    if all_valid:
        print("All output files are valid!")
        return 0
    else:
        print("Some output files failed validation.")
        return 1


if __name__ == "__main__":
    exit(main())
