# this_file: src/vexy_stax/images.py
"""Image reading and overlay compositing."""

import os
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

from PIL import Image


class ImageInfo(TypedDict):
    """Metadata for a single input image."""

    path: str  # Absolute path to the image file
    width: int  # Image width in pixels (= points in Blender)
    height: int  # Image height in pixels (= points in Blender)


def read_images(paths: Sequence[str | Path]) -> list[ImageInfo]:
    """Read each image path and return list of ImageInfo dicts.

    Resolves paths to absolute, verifies existence, reads dimensions via Pillow.
    """
    result: list[ImageInfo] = []
    for img_path in paths:
        abs_path = str(Path(img_path).resolve())
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Image not found: {abs_path}")
        with Image.open(abs_path) as im:
            w, h = im.size
        result.append(ImageInfo(path=abs_path, width=w, height=h))
    return result


def overlay_images(image_infos: list[ImageInfo], output_path: str | Path) -> None:
    """Composite images with horizontal centering and bottom alignment.

    Images are layered in order: index 0 = back-most, last = front-most.
    Canvas size = max(widths) x max(heights) across all images.
    """
    pil_images: list[Image.Image] = []
    for info in image_infos:
        im = Image.open(info["path"]).convert("RGBA")
        pil_images.append(im)

    if not pil_images:
        return

    canvas_w = max(im.width for im in pil_images)
    canvas_h = max(im.height for im in pil_images)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    for im in pil_images:
        x = (canvas_w - im.width) // 2
        y = canvas_h - im.height  # bottom-aligned
        layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        layer.paste(im, (x, y))
        canvas = Image.alpha_composite(canvas, layer)

    canvas.save(str(output_path), "PNG")
