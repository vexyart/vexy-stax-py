# this_file: tests/test_renderer_context.py

from __future__ import annotations

import pytest

from vexy_stax.renderer.canvas import build_canvas
from vexy_stax.renderer.context import (
    GPUUnavailableError,
    OffscreenConfig,
    create_offscreen_bundle,
    create_offscreen_dependencies,
    probe_gpu,
)


def test_probe_gpu_when_device_available_then_returns_device() -> None:
    sentinel = object()

    def fake_getter(**_: object) -> object:
        return sentinel

    device = probe_gpu(device_getter=fake_getter)

    assert device is sentinel, "Device getter output should be returned"


def test_probe_gpu_when_device_missing_then_raises_gpu_unavailable() -> None:
    def fake_getter(**_: object) -> object:
        raise RuntimeError("no device")

    with pytest.raises(GPUUnavailableError):
        probe_gpu(device_getter=fake_getter)


def test_create_offscreen_dependencies_when_factories_supplied_then_canvas_bundle_builds() -> (
    None
):
    calls: list[str] = []

    def fake_getter() -> object:
        calls.append("device-getter-called")
        return object()

    class DummyCanvas:
        def __init__(self, *, size: tuple[int, int], max_fps: int) -> None:
            self.size = size
            self.max_fps = max_fps

        def close(self) -> None:
            calls.append("canvas-close")

    class DummyRenderer:
        def __init__(self, canvas: DummyCanvas) -> None:
            self.canvas = canvas
            self.closed = False

        def close(self) -> None:
            calls.append("renderer-close")
            self.closed = True

    bundle = create_offscreen_bundle(
        OffscreenConfig(size=(128, 96)),
        device_getter=fake_getter,
        canvas_cls=DummyCanvas,
        renderer_cls=DummyRenderer,
    )

    assert isinstance(bundle.canvas, DummyCanvas), (
        "Canvas should originate from provided class"
    )
    assert bundle.canvas.size == (128, 96), (
        "Canvas factory should receive requested size"
    )
    assert isinstance(bundle.renderer, DummyRenderer), (
        "Renderer should wrap dummy canvas"
    )

    bundle.shutdown()

    assert "device-getter-called" in calls, (
        "Device getter should run during canvas creation"
    )
    assert "renderer-close" in calls, "Renderer.close should be wrapped by shutdown"


def test_create_offscreen_dependencies_when_used_directly_then_build_canvas() -> None:
    def fake_getter(**_: object) -> object:
        return object()

    class DummyCanvas:
        def __init__(self, *, size: tuple[int, int], max_fps: int) -> None:
            self.size = size
            self.max_fps = max_fps

    class DummyRenderer:
        def __init__(self, canvas: DummyCanvas) -> None:
            self.canvas = canvas

    deps = create_offscreen_dependencies(
        device_getter=fake_getter,
        canvas_cls=DummyCanvas,
        renderer_cls=DummyRenderer,
        power_preference="low-power",
    )

    bundle = build_canvas((32, 32), deps)

    assert bundle.canvas.size == (32, 32), (
        "Canvas factory should respect requested size"
    )
    assert isinstance(bundle.renderer, DummyRenderer), "Renderer factory should be used"


def test_create_offscreen_bundle_when_device_getter_fails_then_gpu_unavailable() -> (
    None
):
    def fake_getter(**_: object) -> object:
        raise RuntimeError("no adapter")

    class BadCanvas:
        def __init__(
            self, **_: object
        ) -> None:  # pragma: no cover - should not instantiate
            raise AssertionError("Canvas factory should not run when GPU unavailable")

    class BadRenderer:
        def __init__(
            self, _: object
        ) -> None:  # pragma: no cover - should not instantiate
            raise AssertionError("Renderer factory should not run when GPU unavailable")

    with pytest.raises(GPUUnavailableError):
        create_offscreen_bundle(
            OffscreenConfig(size=(16, 16)),
            device_getter=fake_getter,
            canvas_cls=BadCanvas,
            renderer_cls=BadRenderer,
        )
