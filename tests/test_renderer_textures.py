# this_file: tests/test_renderer_textures.py

from __future__ import annotations

import numpy as np

from vexy_stax.models import SceneImage
from vexy_stax.renderer.textures import TextureDependencies, prepare_texture


def test_prepare_texture_when_hook_supplied_then_factory_and_hook_trigger() -> None:
    image = SceneImage(
        filename="layer.png",
        width=2,
        height=2,
        pixels=np.ones((2, 2, 4), dtype=np.uint8),
    )

    events: list[str] = []

    def make_texture(scene_image: SceneImage) -> dict[str, int]:
        assert scene_image.filename == "layer.png", (
            "Texture factory receives the scene image"
        )
        events.append("factory")
        return {"width": scene_image.width, "height": scene_image.height}

    def upload(texture: dict[str, int]) -> None:
        assert texture == {"width": 2, "height": 2}, (
            "Upload hook receives texture output"
        )
        events.append("upload")

    deps = TextureDependencies(texture_factory=make_texture, upload_hook=upload)

    texture = prepare_texture(image, deps)

    assert texture == {"width": 2, "height": 2}, (
        "prepare_texture should return factory result"
    )
    assert events == ["factory", "upload"], "Factory should run before upload hook"


def test_prepare_texture_when_no_hook_then_returns_factory_result() -> None:
    image = SceneImage(
        filename="layer.png",
        width=1,
        height=1,
        pixels=np.zeros((1, 1, 4), dtype=np.uint8),
    )

    deps = TextureDependencies(texture_factory=lambda item: {"name": item.filename})

    texture = prepare_texture(image, deps)

    assert texture == {"name": "layer.png"}, "Factory output should be used directly"
