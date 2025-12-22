# this_file: tests/test_renderer_materials.py

from __future__ import annotations

import numpy as np
import pygfx as gfx
import pytest

from vexy_stax.renderer.materials import build_material, parse_hex_colour


def test_parse_hex_colour_when_rgb_then_expands_pairs() -> None:
    colour = parse_hex_colour("#369")
    assert pytest.approx(colour) == (0.2, 0.4, 0.6), "Short hex should expand to rrggbb"


def test_build_material_when_matte_then_uses_standard_material() -> None:
    """Matte preset matches JS MATERIAL_PRESETS.matte (roughness=0.7)."""
    mat = build_material("matte", colour="#4477aa")
    assert isinstance(mat, gfx.MeshStandardMaterial), (
        "Matte preset should use MeshStandardMaterial"
    )
    assert mat.metalness == pytest.approx(0.0)
    assert mat.roughness == pytest.approx(0.7)  # Matches JS constants.js
    assert mat.alpha_mode == "solid"


def test_build_material_when_glossy_then_sets_shininess_and_texture() -> None:
    texture = gfx.Texture(data=np.zeros((1, 1, 4), dtype=np.uint8), dim=2)
    mat = build_material("glossy", colour="#ffffff", texture=texture)
    assert isinstance(mat, gfx.MeshPhongMaterial)
    assert mat.shininess == pytest.approx(80.0)
    assert mat.map.texture is texture


def test_build_material_when_metal_then_enables_metalness() -> None:
    mat = build_material("metal", colour="#cccccc", opacity=0.5)
    assert isinstance(mat, gfx.MeshStandardMaterial)
    assert mat.metalness == pytest.approx(1.0)
    assert mat.alpha_mode == "blend"
    assert mat.opacity == pytest.approx(0.5)


def test_build_material_when_glass_then_forces_transparency() -> None:
    mat = build_material("glass", colour="#88ddff", opacity=0.3)
    assert isinstance(mat, gfx.MeshStandardMaterial)
    assert mat.alpha_mode == "blend"
    assert mat.roughness == pytest.approx(0.05)


def test_build_material_when_basic_then_uses_unlit_material() -> None:
    """Basic preset uses MeshBasicMaterial for unlit rendering (hero culmination)."""
    texture = gfx.Texture(data=np.zeros((1, 1, 4), dtype=np.uint8), dim=2)
    mat = build_material("basic", colour="#ffffff", texture=texture)
    assert isinstance(mat, gfx.MeshBasicMaterial), (
        "Basic preset should use MeshBasicMaterial (unlit)"
    )
    assert mat.map.texture is texture
    # Basic material renders without lighting for flat composite appearance
    assert mat.alpha_mode == "blend"


def test_build_material_when_unknown_preset_then_errors() -> None:
    with pytest.raises(ValueError):
        build_material("unknown", colour="#000000")
