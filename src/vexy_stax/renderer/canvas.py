# this_file: vexy-stax-py/src/vexy_stax/renderer/canvas.py
"""Canvas scaffolding that keeps pygfx interactions behind small seams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

ShutdownFactory = Callable[[Any, Any], Callable[[], None]]


@dataclass(slots=True, frozen=True)
class CanvasDependencies:
    """Factories required to assemble a renderer-capable canvas."""

    canvas_factory: Callable[[tuple[int, int]], Any]
    renderer_factory: Callable[[Any], Any]
    shutdown_factory: ShutdownFactory | None = None


@dataclass(slots=True, frozen=True)
class CanvasBundle:
    """Container bundling canvas, renderer, and shutdown hook."""

    canvas: Any
    renderer: Any
    shutdown: Callable[[], None]


def build_canvas(size: tuple[int, int], deps: CanvasDependencies) -> CanvasBundle:
    """Create a canvas/renderer pair with predictable teardown.

    The dependency object allows tests to provide fakes while production code can
    pass pygfx factories. When no explicit ``shutdown_factory`` is provided the
    helper falls back to ``renderer.close`` or ``canvas.close`` if either exists.
    """

    canvas = deps.canvas_factory(size)
    renderer = deps.renderer_factory(canvas)

    if deps.shutdown_factory is not None:
        shutdown = deps.shutdown_factory(canvas, renderer)
    else:
        shutdown = _infer_shutdown(canvas, renderer)

    return CanvasBundle(canvas=canvas, renderer=renderer, shutdown=shutdown)


def _infer_shutdown(canvas: Any, renderer: Any) -> Callable[[], None]:
    candidates = [getattr(renderer, "close", None), getattr(canvas, "close", None)]
    for candidate in candidates:
        wrapped = _wrap_shutdown(candidate)
        if wrapped is not None:
            return wrapped

    return lambda: None


def _wrap_shutdown(candidate: Any) -> Callable[[], None] | None:
    if not callable(candidate):
        return None

    def _wrapped() -> None:
        candidate()

    return _wrapped


__all__ = ["CanvasBundle", "CanvasDependencies", "build_canvas"]
