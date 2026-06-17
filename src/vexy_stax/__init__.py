# this_file: src/vexy_stax/__init__.py
"""vexy-stax: render layered PNGs as 3D glass plates from a shared JSON scene format."""

try:
    from vexy_stax._version import __version__
except ImportError:  # pragma: no cover - fallback when not built
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
