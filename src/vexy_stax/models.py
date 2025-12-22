# this_file: src/vexy_stax/models.py
"""Data structures describing vexy-stax scene payloads and runtime objects."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field, field_validator


@dataclass(slots=True)
class SceneImage:
    """Decoded image ready for rendering."""

    filename: str
    width: int
    height: int
    pixels: np.ndarray


@dataclass(slots=True)
class SceneParams:
    """Normalized scene parameters."""

    z_spacing: float
    bg_color: str
    transparent_bg: bool
    camera_mode: str
    camera_fov: float | None
    camera_zoom: float | None


@dataclass(slots=True)
class SceneCamera:
    """Camera placement loaded from the JSON scene."""

    x: float
    y: float
    z: float


@dataclass(slots=True)
class SceneSettings:
    """Visual settings from the scene JSON."""

    viewpoint: str
    material: str
    material_thickness: float
    floor_opacity: float
    ambient_mode: bool


@dataclass(slots=True)
class SceneConfig:
    """Fully decoded scene ready for the renderer."""

    version: str
    params: SceneParams
    images: list[SceneImage]
    camera: SceneCamera | None
    settings: SceneSettings | None = None


class _SceneImagePayload(BaseModel):
    filename: str
    data_url: str = Field(alias="dataURL")
    width: int | None = None
    height: int | None = None


class _SceneParamsPayload(BaseModel):
    z_spacing: float = Field(alias="zSpacing")
    bg_color: str = Field(alias="bgColor")
    transparent_bg: bool = Field(alias="transparentBg", default=False)
    camera_mode: str = Field(alias="cameraMode", default="perspective")
    camera_fov: float | None = Field(alias="cameraFOV", default=None)
    camera_zoom: float | None = Field(alias="cameraZoom", default=None)

    @field_validator("bg_color")
    @classmethod
    def _validate_color(cls, value: str) -> str:
        if (
            not isinstance(value, str)
            or not value.startswith("#")
            or len(value) not in {4, 7}
        ):
            msg = "Background colour must be a hex string like #fff or #ffffff"
            raise ValueError(msg)
        return value

    @field_validator("camera_mode")
    @classmethod
    def _validate_camera_mode(cls, value: str) -> str:
        allowed = {"perspective", "telephoto", "orthographic"}
        if value not in allowed:
            raise ValueError(f"cameraMode must be one of {sorted(allowed)}")
        return value

    @field_validator("z_spacing")
    @classmethod
    def _validate_z_spacing(cls, value: float) -> float:
        if value < 0:
            raise ValueError("zSpacing must be non-negative")
        return value


class _SceneCameraPayload(BaseModel):
    class Position(BaseModel):
        x: float
        y: float
        z: float

    position: Position


class _SceneSettingsPayload(BaseModel):
    viewpoint: str = "beauty"
    material: str = "glossy"
    material_thickness: float = Field(alias="materialThickness", default=0.0)
    floor_opacity: float = Field(alias="floorOpacity", default=0.01)
    ambient_mode: bool = Field(alias="ambientMode", default=False)


class _SceneConfigPayload(BaseModel):
    version: str
    params: _SceneParamsPayload
    images: list[_SceneImagePayload]
    camera: _SceneCameraPayload | None = None
    settings: _SceneSettingsPayload | None = None


__all__ = [
    "SceneConfig",
    "SceneParams",
    "SceneImage",
    "SceneCamera",
    "SceneSettings",
    "_SceneConfigPayload",
    "_SceneParamsPayload",
    "_SceneImagePayload",
    "_SceneCameraPayload",
    "_SceneSettingsPayload",
]
