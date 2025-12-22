# this_file: vexy-stax-py/src/vexy_stax/renderer/materials.py
"""Material helpers translating vexy-stax presets into pygfx objects."""

from __future__ import annotations

from typing import Any
from collections.abc import Callable

import pygfx as gfx

MaterialFactory = Callable[[tuple[float, float, float], Any, float], Any]


def parse_hex_colour(value: str) -> tuple[float, float, float]:
    """Convert ``#rgb`` or ``#rrggbb`` into linear RGB floats."""

    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(part * 2 for part in value)
    if len(value) != 6:
        raise ValueError("Hex colours must be #rgb or #rrggbb")

    red = int(value[0:2], 16) / 255.0
    green = int(value[2:4], 16) / 255.0
    blue = int(value[4:6], 16) / 255.0
    return (red, green, blue)


def _matte(rgb: tuple[float, float, float], texture: Any, opacity: float) -> Any:
    # Matte: diffuse surface (roughness=0.7 matches JS MATERIAL_PRESETS.matte)
    # Always use "blend" when texture is present - texture may have alpha channel
    return gfx.MeshStandardMaterial(
        color=rgb,
        metalness=0.0,
        roughness=0.7,
        opacity=opacity,
        alpha_mode="blend" if texture else ("blend" if opacity < 1.0 else "solid"),
        map=texture,
    )


def _glossy(rgb: tuple[float, float, float], texture: Any, opacity: float) -> Any:
    return gfx.MeshPhongMaterial(
        color=rgb,
        shininess=80.0,
        map=texture,
        opacity=opacity,
        alpha_mode="blend" if texture else ("blend" if opacity < 1.0 else "solid"),
    )


def _metal(rgb: tuple[float, float, float], texture: Any, opacity: float) -> Any:
    return gfx.MeshStandardMaterial(
        color=rgb,
        metalness=1.0,
        roughness=0.2,
        opacity=opacity,
        alpha_mode="blend" if texture else ("blend" if opacity < 1.0 else "solid"),
        map=texture,
    )


def _glass(rgb: tuple[float, float, float], texture: Any, opacity: float) -> Any:
    return gfx.MeshStandardMaterial(
        color=rgb,
        metalness=0.0,
        roughness=0.05,
        opacity=opacity,
        alpha_mode="blend",  # glass always needs blend
        map=texture,
    )


def _basic(rgb: tuple[float, float, float], texture: Any, opacity: float) -> Any:
    """Unlit material - renders texture without lighting effects.

    Used at hero shot culmination for flat composite appearance.
    """
    return gfx.MeshBasicMaterial(
        color=rgb,
        map=texture,
        opacity=opacity,
        alpha_mode="blend" if texture else ("blend" if opacity < 1.0 else "solid"),
    )


_PRESETS: dict[str, MaterialFactory] = {
    # Primary presets (matching JS)
    "glossy": _glossy,
    "neutral": _glass,  # neutral is glass-like appearance (default)
    "matte": _matte,
    # Extended presets
    "metal": _metal,
    "glass": _glass,
    "metallic-card": _metal,
    "metal-sheet": _metal,  # alias for metal
    "flat-matte": _matte,
    "glossy-photo": _glossy,
    # Unlit preset for hero shot culmination
    "basic": _basic,
}


def build_material(
    preset: str,
    *,
    colour: str,
    texture: Any | None = None,
    opacity: float = 1.0,
) -> Any:
    """Return a pygfx material for the requested preset."""

    factory = _PRESETS.get(preset.lower())
    if factory is None:
        allowed = ", ".join(sorted(_PRESETS))
        raise ValueError(f"Unknown material preset '{preset}'. Allowed: {allowed}")

    rgb = parse_hex_colour(colour)
    return factory(rgb, texture, opacity)


__all__ = ["build_material", "parse_hex_colour"]
