# this_file: tests/test_renderer_export.py

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vexy_stax.renderer.canvas import CanvasBundle
from vexy_stax.renderer.export import (
    PNGExportResult,
    VideoExportError,
    VideoExportResult,
    export_png,
    export_video,
)


class FakeCanvas:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def set_logical_size(self, width: int, height: int) -> None:
        self.calls.append((width, height))


def _rgba(width: int, height: int) -> np.ndarray:
    data = np.zeros((height, width, 4), dtype=np.uint8)
    data[..., :3] = 128
    data[..., 3] = 255
    return data


def test_export_png_when_scale_two_then_canvas_resized_and_writer_called(
    tmp_path: Path,
) -> None:
    canvas = FakeCanvas()
    bundle = CanvasBundle(canvas=canvas, renderer=object(), shutdown=lambda: None)

    written: dict[str, np.ndarray] = {}

    def render_fn(bundle: CanvasBundle, scene: object, camera: object) -> np.ndarray:
        return _rgba(200, 100)

    def writer(path: str, image: np.ndarray) -> None:
        written[path] = image

    result = export_png(
        bundle=bundle,
        scene=object(),
        camera=object(),
        output_path=tmp_path / "frame.png",
        width=200,
        height=100,
        scale=2,
        render_fn=render_fn,
        writer=writer,
    )

    assert isinstance(result, PNGExportResult)
    assert canvas.calls[-1] == (400, 200), "Canvas should be resized by scale factor"
    assert str(result.path) in written
    assert written[str(result.path)].shape == (100, 200, 4)


def test_export_png_when_parent_directory_missing_then_creates(tmp_path: Path) -> None:
    canvas = FakeCanvas()
    bundle = CanvasBundle(canvas=canvas, renderer=object(), shutdown=lambda: None)

    target = tmp_path / "nested" / "frame.png"
    recorded: dict[str, np.ndarray] = {}

    def render_fn(bundle: CanvasBundle, scene: object, camera: object) -> np.ndarray:
        return _rgba(4, 2)

    def writer(path: str, image: np.ndarray) -> None:
        recorded[path] = image

    export_png(
        bundle=bundle,
        scene=object(),
        camera=object(),
        output_path=target,
        width=4,
        height=2,
        scale=1,
        render_fn=render_fn,
        writer=writer,
    )

    assert target.parent.exists(), "Export should create missing directories"
    assert str(target) in recorded, "Writer should receive full output path"


def test_export_png_when_alpha_missing_then_raises(tmp_path: Path) -> None:
    canvas = FakeCanvas()
    bundle = CanvasBundle(canvas=canvas, renderer=object(), shutdown=lambda: None)

    def render_fn(bundle: CanvasBundle, scene: object, camera: object) -> np.ndarray:
        return np.zeros((10, 10, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        export_png(
            bundle=bundle,
            scene=object(),
            camera=object(),
            output_path=tmp_path / "bad.png",
            width=10,
            height=10,
            scale=1,
            render_fn=render_fn,
            writer=lambda path, image: None,
        )


def test_export_png_when_float_image_then_casts_to_uint8(tmp_path: Path) -> None:
    canvas = FakeCanvas()
    bundle = CanvasBundle(canvas=canvas, renderer=object(), shutdown=lambda: None)

    captured: dict[str, np.ndarray] = {}

    def render_fn(bundle: CanvasBundle, scene: object, camera: object) -> np.ndarray:
        data = np.ones((5, 5, 4), dtype=np.float32)
        data[..., 3] = 0.5
        return data * 255

    def writer(path: str, image: np.ndarray) -> None:
        captured[path] = image

    export_png(
        bundle=bundle,
        scene=object(),
        camera=object(),
        output_path=tmp_path / "float.png",
        width=5,
        height=5,
        scale=1,
        render_fn=render_fn,
        writer=writer,
    )

    image = captured[str(tmp_path / "float.png")]
    assert image.dtype == np.uint8
    assert image[..., 3].min() > 0


def test_export_video_when_first_codec_succeeds(tmp_path: Path) -> None:
    frames = [_rgba(10, 10) for _ in range(3)]
    used: list[str] = []

    class DummyWriter:
        def __init__(self, codec: str) -> None:
            self.codec = codec
            self.frames: list[np.ndarray] = []

        def __enter__(self) -> DummyWriter:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def append_data(self, frame: np.ndarray) -> None:
            self.frames.append(frame)

    def factory(path: str, **kwargs: object) -> DummyWriter:
        codec = kwargs.get("codec", "auto")
        used.append(codec)
        return DummyWriter(codec)

    result = export_video(
        output_path=tmp_path / "clip.mp4",
        frames=frames,
        fps=30,
        writer_factory=factory,
    )

    assert isinstance(result, VideoExportResult)
    assert result.codec in {"libx264", "h264", "auto"}
    assert result.frames == 3
    assert used[0] == result.codec or used[0] == "auto"


def test_export_video_when_first_codec_fails_then_uses_fallback(tmp_path: Path) -> None:
    frames = [_rgba(5, 5) for _ in range(2)]
    attempts: list[str] = []

    class DummyWriter:
        def __init__(self, codec: str) -> None:
            self.codec = codec

        def __enter__(self) -> DummyWriter:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def append_data(self, frame: np.ndarray) -> None:
            pass

    def factory(path: str, **kwargs: object) -> DummyWriter:
        codec = kwargs.get("codec", "auto")
        attempts.append(codec)
        if len(attempts) == 1:
            raise RuntimeError("codec unavailable")
        return DummyWriter(codec)

    result = export_video(
        output_path=tmp_path / "clip.mp4",
        frames=frames,
        fps=24,
        writer_factory=factory,
    )

    assert result.frames == 2
    assert len(attempts) >= 2


def test_export_video_when_no_frames_then_error(tmp_path: Path) -> None:
    with pytest.raises(VideoExportError):
        export_video(output_path=tmp_path / "empty.mp4", frames=[], fps=30)
