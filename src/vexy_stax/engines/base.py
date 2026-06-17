# this_file: src/vexy_stax/engines/base.py
"""Engine protocol + lazy registry for the three render backends.

Engines are registered by name. Availability is probed without importing heavy
dependencies at module load: we only check for a binary on PATH or whether a
module is importable. The concrete engines are stubs for now.
"""

from __future__ import annotations

import importlib.util
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from vexy_stax.scene import Scene, View


@runtime_checkable
class Engine(Protocol):
    """A render backend. See SPEC.md §5.1."""

    name: str

    def render_image(self, scene: Scene, view: View, out: Path) -> None: ...

    def render_video(self, scene: Scene, out: Path) -> None: ...


_REGISTRY: dict[str, Engine] = {}

# Map engine name -> a zero-cost availability probe.
_PROBES: dict[str, Callable[[], bool]] = {
    "blender": lambda: shutil.which("blender") is not None,
    "pygfx": lambda: importlib.util.find_spec("pygfx") is not None,
    "playwright": lambda: importlib.util.find_spec("playwright") is not None,
}


def register(engine: Engine) -> Engine:
    """Register an engine instance by its ``name``."""
    _REGISTRY[engine.name] = engine
    return engine


def get_engine(name: str) -> Engine:
    """Return the registered engine named ``name``.

    Importing the engines package registers all known engines lazily.
    """
    _ensure_loaded()
    if name not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown engine {name!r}. Registered: {known}")
    return _REGISTRY[name]


def is_available(name: str) -> bool:
    """Probe whether engine ``name``'s dependency is present (no heavy import)."""
    probe = _PROBES.get(name)
    return bool(probe and probe())


def available_engines() -> list[str]:
    """Names of engines whose dependencies are present, in registration order."""
    _ensure_loaded()
    return [name for name in _REGISTRY if is_available(name)]


def all_engines() -> list[str]:
    """All registered engine names regardless of availability."""
    _ensure_loaded()
    return list(_REGISTRY)


def _ensure_loaded() -> None:
    """Import the engine stub modules so they self-register (idempotent)."""
    if _REGISTRY:
        return
    from vexy_stax.engines import blender, playwright, pygfx  # noqa: F401
