# this_file: vexy-stax-py/src/vexy_stax/renderer/__init__.py
"""Renderer scaffolding helpers built around dependency injection.

These modules expose small building blocks so tests can supply fakes while the
production code wires in pygfx/wgpu primitives.
"""

from .canvas import CanvasBundle, CanvasDependencies, build_canvas
from .camera import (
    SpacingTimeline,
    build_spacing_timeline,
    ease_power2_in_out,
    make_camera,
)
from .context import (
    GPUUnavailableError,
    OffscreenConfig,
    create_offscreen_bundle,
    create_offscreen_dependencies,
    probe_gpu,
)
from .export import (
    PNGExportResult,
    VideoExportError,
    VideoExportResult,
    export_png,
    export_video,
)
from .materials import build_material, parse_hex_colour
from .scene_builder import SceneBuilderDependencies, build_scene
from .textures import TextureDependencies, prepare_texture

__all__ = [
    "CanvasBundle",
    "CanvasDependencies",
    "GPUUnavailableError",
    "OffscreenConfig",
    "PNGExportResult",
    "SceneBuilderDependencies",
    "TextureDependencies",
    "SpacingTimeline",
    "build_material",
    "create_offscreen_bundle",
    "create_offscreen_dependencies",
    "build_canvas",
    "build_scene",
    "VideoExportError",
    "VideoExportResult",
    "build_spacing_timeline",
    "export_png",
    "export_video",
    "ease_power2_in_out",
    "make_camera",
    "parse_hex_colour",
    "probe_gpu",
    "prepare_texture",
]
