# this_file: tests/test_renderer_scene_builder.py

from __future__ import annotations

import numpy as np

from vexy_stax.models import SceneConfig, SceneImage, SceneParams
from vexy_stax.renderer.scene_builder import (
    SceneBuilderDependencies,
    build_scene,
)


def _make_scene_params() -> SceneParams:
    return SceneParams(
        z_spacing=0.5,
        bg_color="#000000",
        transparent_bg=False,
        camera_mode="perspective",
        camera_fov=None,
        camera_zoom=None,
    )


def test_build_scene_when_dependencies_provided_then_constructs_meshes() -> None:
    pixels = np.zeros((1, 1, 4), dtype=np.uint8)
    images = [
        SceneImage(filename="layer1.png", width=1, height=1, pixels=pixels),
        SceneImage(filename="layer2.png", width=1, height=1, pixels=pixels),
    ]

    config = SceneConfig(
        version="1.0",
        params=_make_scene_params(),
        images=images,
        camera=None,
    )

    calls: list[str] = []

    class DummyScene:
        def __init__(self) -> None:
            self.nodes: list[str] = []

        def add(self, mesh: str) -> None:
            self.nodes.append(mesh)

    def scene_factory() -> DummyScene:
        calls.append("scene")
        return DummyScene()

    def geometry_factory(image: SceneImage) -> str:
        calls.append(f"geometry:{image.filename}")
        return f"geom:{image.filename}"

    def material_factory(image: SceneImage, texture: str) -> str:
        assert texture.startswith("tex"), (
            "Texture should be forwarded to material factory"
        )
        calls.append(f"material:{image.filename}")
        return f"mat:{image.filename}"

    def mesh_factory(geometry: str, material: str) -> str:
        calls.append(f"mesh:{geometry}:{material}")
        return f"mesh:{geometry}:{material}"

    def placement(mesh: str, image: SceneImage, index: int, spacing: float) -> None:
        calls.append(f"place:{mesh}:{index}:{spacing}")

    deps = SceneBuilderDependencies(
        scene_factory=scene_factory,
        geometry_factory=geometry_factory,
        material_factory=material_factory,
        mesh_factory=mesh_factory,
        placement=placement,
    )

    scene = build_scene(config, ["tex1", "tex2"], deps)

    assert isinstance(scene, DummyScene), "Scene factory should supply DummyScene"
    assert scene.nodes == [
        "mesh:geom:layer1.png:mat:layer1.png",
        "mesh:geom:layer2.png:mat:layer2.png",
    ], "Meshes should be added to scene in order"

    assert calls == [
        "scene",
        "geometry:layer1.png",
        "material:layer1.png",
        "mesh:geom:layer1.png:mat:layer1.png",
        "place:mesh:geom:layer1.png:mat:layer1.png:0:0.5",
        "geometry:layer2.png",
        "material:layer2.png",
        "mesh:geom:layer2.png:mat:layer2.png",
        "place:mesh:geom:layer2.png:mat:layer2.png:1:0.5",
    ], "Factories and placement should run in sequence per layer"


def test_build_scene_when_texture_mismatch_then_raises_value_error() -> None:
    config = SceneConfig(
        version="1.0",
        params=_make_scene_params(),
        images=[
            SceneImage(
                filename="layer.png",
                width=1,
                height=1,
                pixels=np.zeros((1, 1, 4), dtype=np.uint8),
            )
        ],
        camera=None,
    )

    deps = SceneBuilderDependencies(
        scene_factory=lambda: object(),
        geometry_factory=lambda image: image,
        material_factory=lambda image, texture: (image, texture),
        mesh_factory=lambda geometry, material: (geometry, material),
    )

    try:
        build_scene(config, [], deps)
    except ValueError as exc:
        assert "Texture list" in str(exc), "Mismatch should raise a helpful error"
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for texture mismatch")
