#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pillow"]
# ///
# this_file: create_test_images.py
"""Create simple colored test images to verify stacking."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Create test images directory
test_dir = Path(__file__).parent / "test-img"
test_dir.mkdir(exist_ok=True)

# Create three distinct colored layers
colors = [
    ("#FF6B6B", "Layer 1 - Red"),  # Red
    ("#4ECDC4", "Layer 2 - Cyan"),  # Cyan
    ("#FFE66D", "Layer 3 - Yellow"),  # Yellow
]

size = (400, 300)

for i, (color, label) in enumerate(colors, 1):
    # Create image with solid color
    img = Image.new("RGBA", size, color)
    draw = ImageDraw.Draw(img)

    # Add label
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
    except OSError:
        font = ImageFont.load_default()

    # Draw text with black outline for visibility
    text_pos = (size[0] // 2 - 100, size[1] // 2 - 24)
    draw.text(text_pos, label, fill="black", font=font)

    # Save
    output = test_dir / f"layer{i}.png"
    img.save(output)
    print(f"Created {output}")

print(f"\nTest images created in {test_dir}/")
