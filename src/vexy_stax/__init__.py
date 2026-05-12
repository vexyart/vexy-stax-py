# this_file: vexy-stax-py/src/vexy_stax/__init__.py
"""vexy-stax-py: headless 3D renderer for vexy-stax JSON scenes.

Renders the same JSON scene format used by the vexy-stax-js browser editor,
producing PNG stills and MP4/MOV animations without a browser.

Two backends:

- **pygfx** (default) — GPU rendering via wgpu (Metal / Vulkan / DirectX).
  Fast, headless, no browser required. Use ``vexy-stax doctor`` to check GPU.
- **playwright** (optional, ``pip install vexy-stax[browser]``) — drives the
  vexy-stax-js web app via browser automation for pixel-perfect parity.

Quick start::

    # Check GPU
    vexy-stax doctor

    # Render a PNG still
    vexy-stax render scene.json output.png

    # Export a hero-shot animation
    vexy-stax animate scene.json hero.mp4

    # Create a test scene
    vexy-stax-create-test  # writes test-img/layer123.json

Scene format: JSON with base64-encoded image data, camera/material settings,
and animation parameters. Shared with vexy-stax-js for round-trip compatibility.
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
