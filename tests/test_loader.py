# this_file: tests/test_loader.py
"""Tests for the scene loader and validators."""

from __future__ import annotations

import json
import base64
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from vexy_stax.loader import LoaderError, load_scene_config


def test_load_scene_config_when_file_missing_then_raises_runtime_error(
    tmp_path: Path,
) -> None:
    target = tmp_path / "missing.json"

    with pytest.raises(LoaderError) as exc:
        load_scene_config(target)

    assert "missing" in str(exc.value).lower()


def test_load_scene_config_when_schema_invalid_then_reports_field(
    tmp_path: Path,
) -> None:
    bad_payload = {"version": "1.0", "params": {"zSpacing": 10}}
    target = tmp_path / "invalid.json"
    target.write_text(json.dumps(bad_payload))

    with pytest.raises(LoaderError) as exc:
        load_scene_config(target)

    message = str(exc.value).lower()
    assert "images" in message


def test_load_scene_config_when_valid_scene_then_decodes_images(
    project_root: Path,
) -> None:
    scene_path = project_root.parent / "test-data/slides/slides_scene.json"

    config = load_scene_config(scene_path)

    assert config.version == "1.0"
    assert config.params.z_spacing is not None or config.params.z_spacing == 0
    assert len(config.images) >= 1

    first_image = config.images[0]
    assert first_image.width > 0
    assert first_image.height > 0
    assert first_image.pixels.dtype == np.uint8
    assert first_image.pixels.ndim == 3
    assert first_image.pixels.shape[2] == 4
    assert np.max(first_image.pixels[:, :, 3]) > 0


def test_load_scene_config_when_base64_invalid_then_raises(tmp_path: Path) -> None:
    payload = {
        "version": "1.0",
        "params": {"zSpacing": 10, "bgColor": "#ffffff"},
        "images": [
            {
                "filename": "broken.png",
                "dataURL": "data:image/png;base64,not-base64",
            }
        ],
    }
    target = tmp_path / "broken.json"
    target.write_text(json.dumps(payload))

    with pytest.raises(LoaderError) as exc:
        load_scene_config(target)

    assert "base64" in str(exc.value).lower()


def test_load_scene_config_when_jpeg_payload_then_decodes_raster(
    tmp_path: Path,
) -> None:
    image = Image.new("RGB", (3, 2), color=(25, 50, 75))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    payload = {
        "version": "1.0",
        "params": {
            "zSpacing": 5,
            "bgColor": "#000000",
            "transparentBg": False,
        },
        "images": [
            {
                "filename": "layer.jpg",
                "dataURL": f"data:image/jpeg;base64,{encoded}",
            }
        ],
    }

    target = tmp_path / "jpeg_scene.json"
    target.write_text(json.dumps(payload))

    config = load_scene_config(target)

    assert len(config.images) == 1
    decoded = config.images[0]
    assert decoded.width == 3
    assert decoded.height == 2
    assert decoded.pixels.shape == (2, 3, 4)
    assert decoded.pixels.dtype == np.uint8
    assert np.any(decoded.pixels[..., 3]), "JPEG data should promote to opaque RGBA"


def test_load_scene_config_when_mime_not_supported_then_raises(tmp_path: Path) -> None:
    encoded_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    payload = {
        "version": "1.0",
        "params": {"zSpacing": 10, "bgColor": "#ffffff"},
        "images": [
            {
                "filename": "invalid.png",
                "dataURL": f"data:text/plain;base64,{encoded_pixel}",
            }
        ],
    }
    target = tmp_path / "invalid_mime.json"
    target.write_text(json.dumps(payload))

    with pytest.raises(LoaderError) as exc:
        load_scene_config(target)

    message = str(exc.value).lower()
    assert "mime" in message


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
