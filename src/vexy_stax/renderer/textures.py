# this_file: vexy-stax-py/src/vexy_stax/renderer/textures.py
"""Texture helpers based on dependency injection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

from ..models import SceneImage


@dataclass(slots=True, frozen=True)
class TextureDependencies:
    """Factories responsible for turning ``SceneImage`` data into GPU textures."""

    texture_factory: Callable[[SceneImage], Any]
    upload_hook: Callable[[Any], None] | None = None


def prepare_texture(image: SceneImage, deps: TextureDependencies) -> Any:
    """Convert a decoded image into a texture, invoking optional upload hooks."""

    texture = deps.texture_factory(image)

    if deps.upload_hook is not None:
        deps.upload_hook(texture)

    return texture


__all__ = ["TextureDependencies", "prepare_texture"]
