# this_file: vexy-stax-py/src/vexy_stax/__init__.py
"""Vexy Stax - Python automation for vexy-stax-js web application.

Main exports:
    VexyStaxBrowser: Playwright-based browser automation class
    __version__: Package version string
"""

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

from .browser import VexyStaxBrowser

__all__ = ["VexyStaxBrowser", "__version__"]
