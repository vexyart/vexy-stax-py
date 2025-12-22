# this_file: tests/test_renderer_canvas.py

from __future__ import annotations

from vexy_stax.renderer.canvas import CanvasDependencies, build_canvas


def test_build_canvas_when_shutdown_factory_provided_then_custom_hook_runs() -> None:
    calls: list[str] = []

    def make_canvas(size: tuple[int, int]) -> dict[str, tuple[int, int]]:
        calls.append(f"canvas:{size}")
        return {"size": size}

    def make_renderer(canvas: dict[str, tuple[int, int]]) -> dict[str, tuple[int, int]]:
        calls.append(f"renderer:{canvas['size']}")
        return {"canvas": canvas}

    def shutdown(canvas: object, renderer: object) -> callable:
        def _shutdown() -> None:
            calls.append("shutdown")

        return _shutdown

    deps = CanvasDependencies(
        canvas_factory=make_canvas,
        renderer_factory=make_renderer,
        shutdown_factory=shutdown,
    )

    bundle = build_canvas((800, 600), deps)

    assert bundle.canvas == {"size": (800, 600)}, (
        "Canvas factory should receive requested size"
    )
    assert bundle.renderer == {"canvas": {"size": (800, 600)}}, (
        "Renderer factory should receive canvas"
    )

    bundle.shutdown()

    assert calls == [
        "canvas:(800, 600)",
        "renderer:(800, 600)",
        "shutdown",
    ], "Dependency hooks should record canvas, renderer, and shutdown order"


def test_build_canvas_when_no_shutdown_factory_then_falls_back_to_close() -> None:
    class DummyRenderer:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    renderer = DummyRenderer()

    def make_canvas(size: tuple[int, int]) -> dict[str, tuple[int, int]]:
        return {"size": size}

    def make_renderer(_: dict[str, tuple[int, int]]) -> DummyRenderer:
        return renderer

    deps = CanvasDependencies(
        canvas_factory=make_canvas,
        renderer_factory=make_renderer,
        shutdown_factory=None,
    )

    bundle = build_canvas((1, 1), deps)

    # Renderer.close should be wrapped so that calling shutdown toggles the flag.
    bundle.shutdown()

    assert renderer.closed is True, (
        "Renderer.close should run when shutdown factory missing"
    )
