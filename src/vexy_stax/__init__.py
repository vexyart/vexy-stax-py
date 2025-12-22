# this_file: vexy-stax-py/src/vexy_stax/__init__.py
"""Vexy Stax - Python automation for vexy-stax-js web application.

Main exports:
    VexyStaxBrowser: Playwright-based browser automation class
    __version__: Package version string
"""

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - fallback for editable install
    __version__ = "0.0.0+unknown"

__all__ = ["VexyStaxBrowser", "__version__"]


def __getattr__(name: str):
    if name == "VexyStaxBrowser":
        from .browser import VexyStaxBrowser as _VexyStaxBrowser

        return _VexyStaxBrowser
    raise AttributeError(name)
