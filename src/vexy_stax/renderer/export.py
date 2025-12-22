# this_file: vexy-stax-py/src/vexy_stax/renderer/export.py
"""PNG export helpers for the pygfx renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import Callable, Iterable, Sequence

import imageio
import imageio.v3 as iio
import numpy as np

from ..config import validate_scale
from .canvas import CanvasBundle

RenderFn = Callable[[CanvasBundle, Any, Any], np.ndarray]
WriterFn = Callable[[str, np.ndarray], None]

VideoWriterFactory = Callable[..., Any]

DEFAULT_VIDEO_CODECS: dict[str, Sequence[str]] = {
    ".mp4": ("libx264", "h264"),
    ".mov": ("prores_ks", "prores"),
}


@dataclass(slots=True, frozen=True)
class PNGExportResult:
    path: Path
    width: int
    height: int
    scale: int


@dataclass(slots=True, frozen=True)
class VideoExportResult:
    path: Path
    codec: str
    frames: int


class VideoExportError(RuntimeError):
    """Raised when no video codec succeeds."""


def export_png(
    *,
    bundle: CanvasBundle,
    scene: Any,
    camera: Any,
    output_path: Path,
    width: int,
    height: int,
    scale: int,
    render_fn: RenderFn | None = None,
    writer: WriterFn | None = None,
) -> PNGExportResult:
    """Render the scene to a PNG with optional supersampling."""

    validate_scale(scale)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scaled_width = int(width * scale)
    scaled_height = int(height * scale)
    _resize_canvas(bundle.canvas, scaled_width, scaled_height)

    render_fn = render_fn or _default_render_fn
    writer = writer or iio.imwrite

    frame = render_fn(bundle, scene, camera)
    rgba = _ensure_rgba(frame)

    writer(str(output_path), rgba)

    return PNGExportResult(
        path=output_path, width=scaled_width, height=scaled_height, scale=scale
    )


ProgressCallback = Callable[[int, int], None]  # (current, total) -> None


def export_video(
    *,
    output_path: Path,
    frames: Iterable[np.ndarray],
    fps: int,
    total_frames: int | None = None,
    on_progress: ProgressCallback | None = None,
    writer_factory: VideoWriterFactory | None = None,
    codec_map: dict[str, Sequence[str]] | None = None,
) -> VideoExportResult:
    """Write frames to a video file, attempting codec fallbacks when necessary.

    Parameters
    ----------
    output_path:
        Where to write the video
    frames:
        Iterable of RGBA numpy arrays
    fps:
        Frames per second
    total_frames:
        Expected frame count (for progress reporting)
    on_progress:
        Callback invoked after each frame with (current, total)
    writer_factory:
        Optional custom writer factory
    codec_map:
        Optional custom codec map
    """
    writer_factory = writer_factory or imageio.get_writer
    codec_map = codec_map or DEFAULT_VIDEO_CODECS

    ext = output_path.suffix.lower()
    candidates = codec_map.get(ext, ("auto",))

    errors: dict[str, Exception] = {}
    for codec in candidates:
        try:
            kwargs: dict[str, Any] = {"fps": fps}
            if codec != "auto":
                kwargs["codec"] = codec
            with writer_factory(str(output_path), **kwargs) as writer:
                frame_count = 0
                for frame in frames:
                    rgba = _ensure_rgba(frame)
                    writer.append_data(rgba)
                    frame_count += 1
                    if on_progress and total_frames:
                        on_progress(frame_count, total_frames)
                if frame_count == 0:
                    raise VideoExportError("Cannot export video without frames")
            return VideoExportResult(
                path=Path(output_path), codec=codec, frames=frame_count
            )
        except VideoExportError:
            raise
        except Exception as exc:  # pragma: no cover - depends on codec availability
            errors[codec] = exc
            continue

    message = "; ".join(f"{codec}: {err}" for codec, err in errors.items())
    raise VideoExportError(f"Failed to encode video {output_path}: {message}")


def _default_render_fn(bundle: CanvasBundle, scene: Any, camera: Any) -> np.ndarray:
    """Default rendering function that renders scene and reads back pixels."""

    # Render scene to canvas
    bundle.renderer.render(scene, camera)

    # Force draw to update canvas buffer
    bundle.canvas.draw()

    # Read pixels from canvas
    img_data = bundle.canvas._last_image
    arr = np.frombuffer(img_data, dtype=np.uint8)

    # Get canvas size
    width, height = bundle.canvas.get_logical_size()

    # Reshape to (height, width, 4)
    return arr.reshape((int(height), int(width), 4))


def _resize_canvas(canvas: Any, width: int, height: int) -> None:
    if hasattr(canvas, "set_logical_size"):
        canvas.set_logical_size(width, height)
    elif hasattr(canvas, "resize"):
        canvas.resize(width, height)


def _ensure_rgba(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] != 4:
        raise ValueError("Renderer must return an RGBA image (H, W, 4)")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    if not np.any(image[..., 3]):
        raise ValueError("Rendered image alpha channel is fully transparent")

    return image


__all__ = [
    "PNGExportResult",
    "ProgressCallback",
    "VideoExportResult",
    "VideoExportError",
    "export_png",
    "export_video",
]
