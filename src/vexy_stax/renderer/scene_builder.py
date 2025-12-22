# this_file: vexy-stax-py/src/vexy_stax/renderer/scene_builder.py
"""Scene composition helpers that defer rendering specifics to dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from ..models import SceneConfig, SceneImage


PlacementHook = Callable[[Any, SceneImage, int, float], None]
AddHook = Callable[[Any, Any], None]


@dataclass(slots=True, frozen=True)
class SceneBuilderDependencies:
    """Factories needed to translate decoded scene data into pygfx objects."""

    scene_factory: Callable[[], Any]
    geometry_factory: Callable[[SceneImage], Any]
    material_factory: Callable[[SceneImage, Any], Any]
    mesh_factory: Callable[[Any, Any], Any]
    add_to_scene: AddHook | None = None
    placement: PlacementHook | None = None


def build_scene(
    config: SceneConfig,
    textures: list[Any],
    deps: SceneBuilderDependencies,
) -> Any:
    """Populate a scene using the provided factories.

    Parameters
    ----------
    config:
        Fully decoded scene configuration.
    textures:
        GPU-ready textures that align with ``config.images``.
    deps:
        Factories and hooks that generate pygfx objects.
    """

    if len(config.images) != len(textures):
        raise ValueError("Texture list must match number of images in the scene")

    scene = deps.scene_factory()

    if deps.add_to_scene is not None:
        add_node = deps.add_to_scene
    else:
        add_method = getattr(scene, "add", None)
        if not callable(add_method):
            raise ValueError("Scene factory must supply an object with an add() method")

        def add_node(scene_obj: Any, mesh: Any) -> None:
            add_method(mesh)

    for index, (image, texture) in enumerate(zip(config.images, textures)):
        geometry = deps.geometry_factory(image)
        material = deps.material_factory(image, texture)
        mesh = deps.mesh_factory(geometry, material)

        if deps.placement is not None:
            deps.placement(mesh, image, index, config.params.z_spacing)

        add_node(scene, mesh)

    return scene


__all__ = ["SceneBuilderDependencies", "build_scene"]
