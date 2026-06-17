#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["fire", "pillow"]
# ///
# this_file: testdata/airbl/border_images.py

import fire
from pathlib import Path
from PIL import Image, ImageDraw


def border_images(
    input_dir: str,
    output_dir: str = None,
    color: str = "444444",
    thickness: int = 4,
) -> None:
    """Add borders to all images in input_dir.

    Args:
        input_dir: Directory containing input images
        output_dir: Directory for output images (optional, overwrites if not provided)
        color: Border color in RRGGBB format (default: f0f0f0)
        thickness: Border thickness in pixels (default: 2)

    Supported formats: PNG, JPEG, BMP, GIF, TIFF, WebP
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise ValueError(f"Input directory not found: {input_dir}")

    # Parse color from RRGGBB to RGB tuple
    if len(color) != 6:
        raise ValueError(f"Color must be 6 hex digits, got: {color}")
    try:
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        raise ValueError(f"Invalid hex color: {color}")

    # Determine output directory
    if output_dir is None:
        output_path = input_path  # Overwrite originals
        overwrite = True
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        overwrite = False

    # Process all images
    supported_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in supported_extensions]

    if not image_files:
        print(f"No supported images found in {input_dir}")
        return

    print(f"Processing {len(image_files)} images...")
    print(f"Color: #{color}, Thickness: {thickness}px")
    print(f"Output: {output_path if overwrite else 'Overwrite originals'}")

    for img_file in image_files:
        try:
            img = Image.open(img_file)
            img = img.convert("RGBA")

            # Draw border inside the image
            draw = ImageDraw.Draw(img)
            width, height = img.size
            t = thickness

            # Draw four rectangles for each edge
            # Top edge
            draw.rectangle([0, 0, width - 1, t - 1], fill=rgb, outline=None)
            # Bottom edge
            draw.rectangle([0, height - t, width - 1, height - 1], fill=rgb, outline=None)
            # Left edge
            draw.rectangle([0, t, t - 1, height - t - 1], fill=rgb, outline=None)
            # Right edge
            draw.rectangle([width - t, t, width - 1, height - t - 1], fill=rgb, outline=None)

            # Save output
            output_file = output_path / img_file.name
            img.save(output_file)
            print(f"  -> {img_file.name}")

        except Exception as e:
            print(f"  ERROR processing {img_file.name}: {e}")

    print("Done!")


if __name__ == "__main__":
    fire.Fire(border_images)
