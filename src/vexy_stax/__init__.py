# this_file: vexy-stax-py/src/vexy_stax/__init__.py
"""Vexy Stax - CLI tool for validating and testing image stacking outputs."""

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
