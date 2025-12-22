# this_file: src/vexy_stax/loader.py
"""Utilities for loading and validating vexy-stax scene JSON exports."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import imageio.v3 as iio
import numpy as np

from .models import (
    SceneCamera,
    SceneConfig,
    SceneImage,
    SceneParams,
    SceneSettings,
    _SceneConfigPayload,
    _SceneImagePayload,
)

DATA_URL_PATTERN = re.compile(
    r"^data:(?P<mime>[^;]+);base64,(?P<payload>.+)$", re.IGNORECASE | re.DOTALL
)

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
}

MIME_EXTENSION_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


class LoaderError(RuntimeError):
    """Raised when a scene file cannot be loaded or validated."""


def load_scene_config(source: Path | str) -> SceneConfig:
    """Load and decode a vexy-stax scene JSON file.

    Parameters
    ----------
    source:
        Path to the JSON file on disk.

    Returns
    -------
    SceneConfig
        Fully decoded scene ready for renderer consumption.
    """

    path = Path(source)
    if not path.exists():
        raise LoaderError(f"Scene file missing: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - rare filesystem error
        raise LoaderError(f"Failed to read scene file: {path}") from exc

    try:
        payload = _SceneConfigPayload.model_validate_json(raw_text)
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Invalid JSON in scene file {path}: {exc.msg}") from exc
    except ValueError as exc:
        raise LoaderError(f"Scene schema invalid for {path}: {exc}") from exc

    params = SceneParams(
        z_spacing=payload.params.z_spacing,
        bg_color=payload.params.bg_color,
        transparent_bg=payload.params.transparent_bg,
        camera_mode=payload.params.camera_mode,
        camera_fov=payload.params.camera_fov,
        camera_zoom=payload.params.camera_zoom,
    )

    camera = None
    if payload.camera is not None:
        camera = SceneCamera(
            x=payload.camera.position.x,
            y=payload.camera.position.y,
            z=payload.camera.position.z,
        )

    settings = None
    if payload.settings is not None:
        settings = SceneSettings(
            viewpoint=payload.settings.viewpoint,
            material=payload.settings.material,
            material_thickness=payload.settings.material_thickness,
            floor_opacity=payload.settings.floor_opacity,
            ambient_mode=payload.settings.ambient_mode,
        )

    images = [_decode_image(entry) for entry in payload.images]

    return SceneConfig(
        version=payload.version,
        params=params,
        images=images,
        camera=camera,
        settings=settings,
    )


def _decode_image(entry: _SceneImagePayload) -> SceneImage:
    match = DATA_URL_PATTERN.match(entry.data_url)
    if not match:
        raise LoaderError(f"Image {entry.filename} is not a base64 data URL")

    mime = match.group("mime").lower()
    if mime not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
        raise LoaderError(
            f"Image {entry.filename} uses unsupported MIME type '{mime}'. "
            f"Supported: {allowed}"
        )

    b64_data = match.group("payload").strip()
    try:
        binary = base64.b64decode(b64_data, validate=True)
    except (base64.binascii.Error, ValueError) as exc:
        raise LoaderError(
            f"Image {entry.filename} contains invalid base64 data"
        ) from exc

    extension = MIME_EXTENSION_MAP[mime]

    try:
        array = iio.imread(binary, extension=extension)
    except Exception as exc:  # pragma: no cover - third-party failure
        raise LoaderError(f"Failed to decode image data for {entry.filename}") from exc

    array = _ensure_rgba(array)

    height, width = array.shape[:2]
    return SceneImage(
        filename=entry.filename,
        width=entry.width or width,
        height=entry.height or height,
        pixels=array,
    )


def _ensure_rgba(array: np.ndarray) -> np.ndarray:
    """Ensure the decoded array is ``uint8`` RGBA."""

    if array.dtype != np.uint8:
        array = np.clip(array, 0, 255).astype(np.uint8)

    if array.ndim == 2:  # grayscale
        alpha = np.full(array.shape, 255, dtype=np.uint8)
        rgb = np.stack([array, array, array], axis=-1)
        return np.concatenate([rgb, alpha[..., None]], axis=-1)

    if array.ndim == 3 and array.shape[2] == 3:
        alpha = np.full(array.shape[:2] + (1,), 255, dtype=np.uint8)
        return np.concatenate([array, alpha], axis=-1)

    if array.ndim == 3 and array.shape[2] == 4:
        return array

    raise LoaderError("Unsupported image format: expected RGB or RGBA channels")


__all__ = ["LoaderError", "load_scene_config"]
