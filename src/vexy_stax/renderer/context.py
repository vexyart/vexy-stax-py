# this_file: vexy-stax-py/src/vexy_stax/renderer/context.py
"""Headless pygfx renderer context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from .canvas import CanvasBundle, CanvasDependencies, build_canvas


class GPUUnavailableError(RuntimeError):
    """Raised when no GPU adapter can be acquired via wgpu."""


DeviceGetter = Callable[..., Any]


def probe_gpu(
    *,
    device_getter: DeviceGetter,
    power_preference: str = "high-performance",
    **kwargs: Any,
) -> Any:
    """Return a GPU device or raise ``GPUUnavailableError`` when not accessible."""

    try:
        # Note: wgpu.utils.get_default_device() doesn't accept arguments in current version
        # power_preference is kept for API compatibility but ignored for now
        return device_getter()
    except RuntimeError as exc:  # pragma: no cover - depends on runtime availability
        raise GPUUnavailableError("No suitable GPU adapter available") from exc


@dataclass(slots=True, frozen=True)
class OffscreenConfig:
    """Configuration for the offscreen renderer context."""

    size: tuple[int, int]
    power_preference: str = "high-performance"


def create_offscreen_dependencies(
    *,
    device_getter: DeviceGetter | None = None,
    canvas_cls: type | None = None,
    renderer_cls: type | None = None,
    power_preference: str = "high-performance",
) -> CanvasDependencies:
    """Assemble ``CanvasDependencies`` backed by pygfx/wgpu primitives."""

    device_getter = device_getter or _default_device_getter
    if canvas_cls is None or renderer_cls is None:
        canvas_cls, renderer_cls = _import_canvas_and_renderer()

    def canvas_factory(size: tuple[int, int]) -> Any:
        probe_gpu(device_getter=device_getter, power_preference=power_preference)
        return canvas_cls(size=size, max_fps=0)

    def renderer_factory(canvas: Any) -> Any:
        return renderer_cls(canvas)

    return CanvasDependencies(
        canvas_factory=canvas_factory,
        renderer_factory=renderer_factory,
    )


def create_offscreen_bundle(
    config: OffscreenConfig,
    *,
    device_getter: DeviceGetter | None = None,
    canvas_cls: type | None = None,
    renderer_cls: type | None = None,
) -> CanvasBundle:
    """Expose a convenience wrapper returning ``CanvasBundle``."""

    deps = create_offscreen_dependencies(
        device_getter=device_getter,
        canvas_cls=canvas_cls,
        renderer_cls=renderer_cls,
        power_preference=config.power_preference,
    )
    return build_canvas(config.size, deps)


def _default_device_getter() -> Any:
    from wgpu.utils import get_default_device

    return get_default_device()


def _import_canvas_and_renderer() -> tuple[type, type]:
    import pygfx as gfx

    try:
        from rendercanvas.offscreen import RenderCanvas as OffscreenCanvas
    except ImportError:
        # Fallback to deprecated wgpu.gui.offscreen
        from wgpu.gui.offscreen import WgpuCanvas as OffscreenCanvas

    return OffscreenCanvas, gfx.renderers.WgpuRenderer


__all__ = [
    "GPUUnavailableError",
    "OffscreenConfig",
    "create_offscreen_bundle",
    "create_offscreen_dependencies",
    "probe_gpu",
]
