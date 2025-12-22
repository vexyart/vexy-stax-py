# this_file: tests/test_create_test_images.py
"""Tests for the create_test_images utility."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from vexy_stax import create_test_images


def test_create_test_images_main_when_run_then_generates_layers(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    create_test_images.main()

    target_dir = tmp_path / "test-img"
    assert target_dir.is_dir(), (
        "Expected create_test_images to create test-img directory"
    )

    generated = sorted(target_dir.glob("layer*.png"))
    assert len(generated) == 3, "Expected exactly three layer PNG files"

    for path in generated:
        assert path.stat().st_size > 0, (
            f"Generated file {path.name} should not be empty"
        )
        with Image.open(path) as image:
            assert image.size == (400, 300), (
                "Generated images should match expected dimensions"
            )
            assert image.mode == "RGBA", "Generated images should include alpha channel"
