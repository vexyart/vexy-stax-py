# this_file: tests/test_renderer_pipeline.py

from __future__ import annotations

from pathlib import Path

import numpy as np

from vexy_stax.config import AnimationDefaults
from vexy_stax.models import SceneConfig, SceneImage, SceneParams
from vexy_stax.renderer import (
    CanvasBundle,
    SceneBuilderDependencies,
    TextureDependencies,
    build_scene,
    build_spacing_timeline,
    export_png,
    export_video,
    make_camera,
    prepare_texture,
)


class StubCanvas:
    def __init__(self) -> None:
        self.sizes: list[tuple[int, int]] = []

    def set_logical_size(self, width: int, height: int) -> None:
        self.sizes.append((width, height))


class StubRenderer:
    def __init__(self) -> None:
        self.rendered: list[tuple[object, object]] = []

    def render(self, scene: object, camera: object) -> np.ndarray:
        self.rendered.append((scene, camera))
        image = np.zeros((16, 16, 4), dtype=np.uint8)
        image[..., :3] = 127
        image[..., 3] = 255
        return image


def _scene_config() -> SceneConfig:
    params = SceneParams(
        z_spacing=0.5,
        bg_color="#000000",
        transparent_bg=False,
        camera_mode="perspective",
        camera_fov=None,
        camera_zoom=None,
    )
    pixels = np.ones((4, 4, 4), dtype=np.uint8) * 255
    images = [
        SceneImage(filename="layer1.png", width=4, height=4, pixels=pixels),
        SceneImage(filename="layer2.png", width=4, height=4, pixels=pixels),
    ]
    return SceneConfig(version="1.0", params=params, images=images, camera=None)


def test_renderer_pipeline_generates_png_and_video(tmp_path: Path) -> None:
    scene = _scene_config()
    textures = []
    deps = TextureDependencies(texture_factory=lambda img: f"texture:{img.filename}")
    for image in scene.images:
        textures.append(prepare_texture(image, deps))

    def _geometry(image) -> str:
        return f"geometry:{image.filename}"

    def _material(image, texture) -> str:
        return f"material:{texture}"

    def _mesh(geometry, material) -> str:
        return f"mesh:{geometry}:{material}"

    canvas_bundle = CanvasBundle(
        canvas=StubCanvas(),
        renderer=StubRenderer(),
        shutdown=lambda: None,
    )

    class SceneCollector(list):
        def add(self, mesh: str) -> None:
            self.append(mesh)

    assembled_scene = build_scene(
        scene,
        textures,
        deps=SceneBuilderDependencies(
            scene_factory=SceneCollector,
            geometry_factory=_geometry,
            material_factory=_material,
            mesh_factory=_mesh,
        ),
    )

    camera = make_camera(scene, aspect_ratio=1.0)
    png_path = tmp_path / "frame.png"

    # Wrap renderer.render to match expected signature
    def render_fn(bundle, scene_obj, camera_obj):
        return bundle.renderer.render(scene_obj, camera_obj)

    result = export_png(
        bundle=canvas_bundle,
        scene=assembled_scene,
        camera=camera,
        output_path=png_path,
        width=scene.images[0].width,
        height=scene.images[0].height,
        scale=1,
        render_fn=render_fn,
        writer=lambda path, image: np.save(Path(path).with_suffix(".npy"), image),
    )

    assert result.path == png_path
    assert (png_path.with_suffix(".npy")).exists()

    timeline = build_spacing_timeline(
        spacing=scene.params.z_spacing,
        defaults=AnimationDefaults(
            fps=10, duration=1.0, hold=0.0, easing="power2.inOut"
        ),
    )
    frames = [
        canvas_bundle.renderer.render(assembled_scene, camera) for _ in timeline.frames
    ]
    video_path = tmp_path / "clip.mp4"

    def writer_factory(path: str, **kwargs: object) -> _VideoWriterStub:
        return _VideoWriterStub()

    video_result = export_video(
        output_path=video_path,
        frames=frames,
        fps=timeline.fps,
        writer_factory=writer_factory,
        codec_map={".mp4": ["auto"]},
    )

    assert video_result.path == video_path
    assert video_result.frames == len(frames)


class _VideoWriterStub:
    def __enter__(self) -> _VideoWriterStub:
        self.frames: list[np.ndarray] = []
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def append_data(self, frame: np.ndarray) -> None:
        self.frames.append(frame)
