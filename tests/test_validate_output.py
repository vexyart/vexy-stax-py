# this_file: tests/test_validate_output.py
"""Unit tests for validate_output.validate_png."""

from pathlib import Path

from PIL import Image

from validate_output import validate_png


def _write_png(
    path: Path, size: tuple[int, int] = (12, 12), color=(200, 20, 20, 255)
) -> None:
    """Write a simple RGBA PNG image."""
    image = Image.new("RGBA", size, color)
    image.save(path, format="PNG")


def test_validate_png_when_file_missing_then_returns_error(tmp_path: Path) -> None:
    target = tmp_path / "missing.png"

    ok, message = validate_png(target, expected_width=10, expected_height=10)

    assert not ok, "Missing files must be flagged as invalid."
    assert "File not found" in message


def test_validate_png_when_not_png_then_reports_format_error(tmp_path: Path) -> None:
    target = tmp_path / "image.jpg"
    Image.new("RGB", (16, 16), "green").save(target, format="JPEG")

    ok, message = validate_png(target, expected_width=16, expected_height=16)

    assert not ok, "Non-PNG files should fail validation."
    assert "not PNG" in message


def test_validate_png_when_dimensions_match_then_returns_true(tmp_path: Path) -> None:
    target = tmp_path / "valid.png"
    _write_png(target, size=(24, 18))

    ok, message = validate_png(target, expected_width=24, expected_height=18)

    assert ok, message
    assert message == ""


def test_validate_png_when_dimensions_mismatch_then_reports_issue(
    tmp_path: Path,
) -> None:
    target = tmp_path / "wrong-size.png"
    _write_png(target, size=(20, 20))

    ok, message = validate_png(target, expected_width=24, expected_height=18)

    assert not ok, "Dimension mismatches must fail validation."
    assert "Width mismatch" in message or "Height mismatch" in message


def test_validate_png_when_blank_transparent_then_reports_blank(tmp_path: Path) -> None:
    target = tmp_path / "blank.png"
    _write_png(target, color=(0, 0, 0, 0))

    ok, message = validate_png(target, expected_width=12, expected_height=12)

    assert not ok, "Blank transparent PNGs must be detected."
    assert "blank" in message.lower()
