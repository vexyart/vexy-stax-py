# this_file: src/vexy_stax/render_pipeline.py
"""End-to-end pygfx rendering pipeline: loader → context → scene → export."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any
from collections.abc import Iterator

import numpy as np
import pygfx as gfx

from .config import DEFAULT_ANIMATION, FLOOR_Y, AnimationDefaults
from .loader import load_scene_config
from .models import SceneConfig
from .renderer.camera import (
    CameraPosition,
    build_hero_timeline,
    calculate_content_center_with_spacing,
    calculate_front_viewpoint,
    make_camera,
)
from .renderer.canvas import CanvasBundle
from .renderer.context import OffscreenConfig, create_offscreen_bundle
from .renderer.export import (
    PNGExportResult,
    ProgressCallback,
    VideoExportResult,
    export_png,
    export_video,
)
from .renderer.materials import build_material
from .renderer.scene_builder import SceneBuilderDependencies, build_scene


def pygfx_render_png(
    scene_json: Path | str,
    output_path: Path | str,
    *,
    width: int = 800,
    height: int = 600,
    scale: int = 1,
) -> PNGExportResult:
    """Render a vexy-stax scene to PNG using pygfx.

    Parameters
    ----------
    scene_json:
        Path to vexy-stax JSON scene file
    output_path:
        Where to write the PNG
    width:
        Canvas width in pixels
    height:
        Canvas height in pixels
    scale:
        Supersampling multiplier (1, 2, or 4)

    Returns
    -------
    PNGExportResult
        Export metadata including final dimensions
    """

    config = load_scene_config(scene_json)
    bundle = create_offscreen_bundle(OffscreenConfig(size=(width, height)))

    try:
        textures = _build_textures(config)
        scene = _build_scene(config, textures)
        aspect_ratio = width / height
        camera = make_camera(config, aspect_ratio=aspect_ratio)

        result = export_png(
            bundle=bundle,
            scene=scene,
            camera=camera,
            output_path=Path(output_path),
            width=width,
            height=height,
            scale=scale,
        )

        return result

    finally:
        bundle.shutdown()


def pygfx_render_video(
    scene_json: Path | str,
    output_path: Path | str,
    *,
    width: int = 800,
    height: int = 600,
    animation: AnimationDefaults | None = None,
    on_progress: ProgressCallback | None = None,
    return_to_start: bool = False,
) -> VideoExportResult:
    """Render a vexy-stax hero animation to video using pygfx.

    Parameters
    ----------
    scene_json:
        Path to vexy-stax JSON scene file
    output_path:
        Where to write the video (.mp4 or .mov)
    width:
        Canvas width in pixels
    height:
        Canvas height in pixels
    animation:
        Animation timing config (defaults to DEFAULT_ANIMATION)
    on_progress:
        Callback invoked after each frame with (current, total)
    return_to_start:
        If True, animation returns to beauty view after hero shot.
        If False (default), animation ends at hero view (straight-on, collapsed).

    Returns
    -------
    VideoExportResult
        Export metadata including codec and frame count
    """

    if animation is None:
        animation = DEFAULT_ANIMATION

    config = load_scene_config(scene_json)
    bundle = create_offscreen_bundle(OffscreenConfig(size=(width, height)))

    try:
        textures = _build_textures(config)

        # Get front slide for hero shot calculation
        if not config.images:
            raise ValueError("Scene must have at least one image for hero animation")
        front_slide = config.images[-1]  # Last image is frontmost

        # Calculate front view position
        fov = config.params.camera_fov or 75.0
        front_slide_index = len(config.images) - 1
        front_view = calculate_front_viewpoint(
            front_slide, width, height, fov, front_slide_index=front_slide_index
        )

        # Get starting camera position and target
        aspect_ratio = width / height
        start_camera = make_camera(config, aspect_ratio=aspect_ratio)
        start_pos = start_camera.world.position
        start_camera_pos = CameraPosition(
            x=start_pos[0], y=start_pos[1], z=start_pos[2]
        )

        # Calculate start target (content center at original spacing)
        start_content_center = calculate_content_center_with_spacing(
            config.images, config.params.z_spacing
        )
        start_target_pos = CameraPosition(
            x=start_content_center[0],
            y=start_content_center[1],
            z=start_content_center[2],
        )

        # Build hero timeline with camera animation
        timeline = build_hero_timeline(
            spacing=config.params.z_spacing,
            start_camera=start_camera_pos,
            start_target=start_target_pos,
            front_view=front_view,
            defaults=animation,
            return_to_start=return_to_start,
        )

        total_frames = len(timeline.spacing_frames)

        # Generate frames by adjusting scene z-spacing and camera over time
        frames = _render_animation_frames(
            bundle=bundle,
            config=config,
            textures=textures,
            timeline=timeline,
            width=width,
            height=height,
        )

        result = export_video(
            output_path=Path(output_path),
            frames=frames,
            fps=animation.fps,
            total_frames=total_frames,
            on_progress=on_progress,
        )

        return result

    finally:
        bundle.shutdown()


def _build_textures(config: SceneConfig) -> list[Any]:
    """Convert scene images to GPU texture maps with proper filtering."""

    texture_maps = []
    for img in config.images:
        # Create pygfx texture from RGBA numpy array with mipmaps
        texture = gfx.Texture(img.pixels, dim=2, generate_mipmaps=True)

        # Wrap in TextureMap with linear filtering for smooth sampling at oblique angles
        # filter="linear" applies to mag, min, and mipmap filtering
        texture_map = gfx.TextureMap(texture, filter="linear")
        texture_maps.append(texture_map)

    return texture_maps


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color like '#1a1a2e' to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b)


def _build_scene(
    config: SceneConfig, textures: list[Any], *, hero_progress: float = 0.0
) -> Any:
    """Assemble pygfx scene with all layers and lighting.

    Parameters
    ----------
    config:
        Scene configuration
    textures:
        GPU-ready texture maps
    hero_progress:
        Animation progress 0.0 (start) → 1.0 (culmination) → 0.0 (end).
        At culmination, uses basic (unlit) material and flat lighting
        so the render matches a simple 2D composite of all slides.
    """

    # Use "basic" (unlit) material to preserve original image appearance.
    # The source images already have good lighting baked in; 3D effect comes
    # from perspective and parallax, not artificial lighting.
    material_preset = "basic"

    def geometry_factory(image: Any) -> Any:
        return gfx.plane_geometry(width=image.width, height=image.height)

    def material_factory(image: Any, texture: Any) -> Any:
        return build_material(material_preset, colour="#FFFFFF", texture=texture)

    def mesh_factory(geometry: Any, material: Any) -> Any:
        return gfx.Mesh(geometry, material)

    def placement_hook(mesh: Any, image: Any, index: int, z_spacing: float) -> None:
        # PLAN.md §1: Final slide at Z=0 (immovable anchor)
        # Formula: z = -(slideCount - 1 - index) * z_spacing
        # This places: index 0 at most negative Z, final index at Z=0
        slide_count = len(config.images)
        offset = (slide_count - 1 - index) * z_spacing
        z_position = -offset if offset != 0 else 0
        # Y = height/2 so bottom of slide sits on floor (Y=0)
        y_position = FLOOR_Y + image.height / 2
        mesh.local.position = (0, y_position, z_position)

    deps = SceneBuilderDependencies(
        scene_factory=gfx.Scene,
        geometry_factory=geometry_factory,
        material_factory=material_factory,
        mesh_factory=mesh_factory,
        placement=placement_hook,
    )

    scene = build_scene(config, textures, deps)

    # Add background color from scene config
    if not config.params.transparent_bg and config.params.bg_color:
        bg_color = _hex_to_rgb(config.params.bg_color)
        background = gfx.Background(None, gfx.BackgroundMaterial(bg_color))
        scene.add(background)

    # Using unlit material, so lighting is minimal (just for any non-textured elements)
    # The _ prefix indicates hero_progress is unused but kept for API compatibility
    _ = hero_progress
    ambient = gfx.AmbientLight(color=(1, 1, 1), intensity=1.0)
    scene.add(ambient)

    return scene


def _render_animation_frames(
    *,
    bundle: CanvasBundle,
    config: SceneConfig,
    textures: list[Any],
    timeline: Any,
    width: int,
    height: int,
) -> Iterator[np.ndarray]:
    """Generate animation frames by adjusting z-spacing, camera, and lighting.

    At hero shot culmination (progress=1), lighting becomes flat and material
    switches to basic for a composite-like appearance matching a simple 2D
    overlay of all slides.
    """

    aspect_ratio = width / height
    fov = config.params.camera_fov or 75.0

    # Create a camera that we'll reposition each frame
    mode = config.params.camera_mode
    if mode == "orthographic":
        img_width = config.images[0].width if config.images else 1
        img_height = config.images[0].height if config.images else 1
        camera = gfx.OrthographicCamera(width=img_width, height=img_height)
    else:
        camera = gfx.PerspectiveCamera(fov=fov, aspect=aspect_ratio)

    # Get spacing, camera position, target, and progress frames from timeline
    spacing_frames = timeline.spacing_frames
    camera_positions = timeline.camera_positions
    camera_targets = timeline.camera_targets
    progress_values = timeline.progress_values

    # Render frame for each timeline step
    for spacing_value, cam_pos, cam_target, hero_progress in zip(
        spacing_frames, camera_positions, camera_targets, progress_values
    ):
        # Update config with current spacing
        frame_config = SceneConfig(
            version=config.version,
            params=replace(config.params, z_spacing=spacing_value),
            images=config.images,
            camera=config.camera,
            settings=config.settings,
        )

        # Rebuild scene with updated spacing and hero progress for lighting/material
        scene = _build_scene(frame_config, textures, hero_progress=hero_progress)

        # Update camera position and target for this frame
        camera.world.position = (cam_pos.x, cam_pos.y, cam_pos.z)
        camera.look_at((cam_target.x, cam_target.y, cam_target.z))

        # Render frame and read pixels
        bundle.renderer.render(scene, camera)
        img_data = bundle.canvas.draw()  # draw() returns memoryview of RGBA image
        frame = np.asarray(img_data)  # Convert to numpy array (no copy)

        yield frame


__all__ = [
    "pygfx_render_png",
    "pygfx_render_video",
]
