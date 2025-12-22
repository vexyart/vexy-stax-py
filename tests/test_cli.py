# this_file: tests/test_cli.py
"""Tests for the Playwright-backed CLI layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from vexy_stax.cli import VexyStaxCLI


class _StubBrowser:
    def __init__(self, url: str | None = None, headless: bool | None = None) -> None:
        self.url = url
        self.headless = headless
        self.launched = False
        self.closed = False
        self.loaded_images: list[list[str]] = []
        self.loaded_configs: list[str] = []
        self.animation_calls: list[dict[str, float]] = []

    def launch(self) -> None:
        self.launched = True

    def close(self) -> None:
        self.closed = True

    def load_images(self, images: list[str]) -> None:
        self.loaded_images.append(images)

    def load_config(self, path: str) -> None:
        self.loaded_configs.append(path)

    def play_animation(
        self, *, duration: float, hold_time: float, easing: str | None = None
    ) -> None:
        self.animation_calls.append(
            {"duration": duration, "hold_time": hold_time, "easing": easing or ""}
        )


def _make_image(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    base = Image.new("RGBA", (10, 10), "#ffffff")
    ext = target.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        base = base.convert("RGB")
    elif ext == ".gif":
        base = base.convert("P")
    base.save(target)


def test_cli_load_images_when_directory_then_uses_png_glob(tmp_path: Path) -> None:
    image_dir = tmp_path / "layers"
    png_path = image_dir / "layer1.png"
    _make_image(png_path)

    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(image_dir))

    assert outcome is True, "Expected CLI helper to succeed for directory inputs"
    assert browser.loaded_images == [[str(png_path)]], "Browser should receive PNG list"


def test_cli_load_images_when_directory_without_images_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(empty_dir))

    assert outcome is False, "Expected failure when directory lacks importable files"
    captured = capsys.readouterr().out
    assert "No image files" in captured


def test_cli_load_images_when_json_then_invokes_load_config(tmp_path: Path) -> None:
    json_path = tmp_path / "scene.json"
    json_path.write_text(json.dumps({"images": []}))

    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(json_path))

    assert outcome is True, "Expected JSON config to load successfully"
    assert browser.loaded_configs == [str(json_path)]


def test_cli_load_images_when_json_uppercase_then_invokes_load_config(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "scene.JSON"
    json_path.write_text(json.dumps({"images": []}))

    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(json_path))

    assert outcome is True
    assert browser.loaded_configs == [str(json_path)]


def test_cli_load_images_when_path_invalid_then_prints_error(
    tmp_path: Path, capsys
) -> None:
    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(tmp_path / "missing"))

    assert outcome is False
    captured = capsys.readouterr().out
    assert "not a valid folder" in captured


def test_cli_load_images_when_mixed_formats_then_sorted_and_filtered(
    tmp_path: Path,
) -> None:
    image_dir = tmp_path / "layers"
    png_path = image_dir / "b_layer.PNG"
    jpg_path = image_dir / "a_layer.jpg"
    gif_path = image_dir / "c_layer.GiF"
    ignored = image_dir / "notes.txt"

    _make_image(png_path)
    _make_image(jpg_path)
    _make_image(gif_path)
    ignored.parent.mkdir(parents=True, exist_ok=True)
    ignored.write_text("skip")

    browser = _StubBrowser()
    cli = VexyStaxCLI()

    outcome = cli._load_images(browser, str(image_dir))

    assert outcome is True
    assert browser.loaded_images == [[str(jpg_path), str(png_path), str(gif_path)]], (
        "Files should be sorted case-insensitively by name and include all supported formats"
    )


def test_cli_launch_when_headless_then_closes_browser(
    monkeypatch, tmp_path: Path
) -> None:
    instances: list[_StubBrowser] = []

    def _factory(*args: Any, **kwargs: Any) -> _StubBrowser:
        browser = _StubBrowser(*args, **kwargs)
        instances.append(browser)
        return browser

    monkeypatch.setattr("vexy_stax.cli.VexyStaxBrowser", _factory)

    assets = tmp_path / "layers"
    png_path = assets / "layer1.png"
    _make_image(png_path)

    cli = VexyStaxCLI()
    cli.launch(images=str(assets), headless=True)

    assert instances, "Expected the CLI to instantiate a browser"
    browser = instances[0]
    assert browser.headless is True
    assert browser.launched is True
    assert browser.closed is True
    assert browser.loaded_images == [[str(png_path)]]


def test_cli_render_when_scale_invalid_then_reports_error(monkeypatch, capsys) -> None:
    instantiated = False

    def _factory(*args: Any, **kwargs: Any) -> _StubBrowser:
        nonlocal instantiated
        instantiated = True
        return _StubBrowser(*args, **kwargs)

    monkeypatch.setattr("vexy_stax.cli.VexyStaxBrowser", _factory)

    cli = VexyStaxCLI()
    cli.render(images="ignored", output="out.png", scale=5)

    assert instantiated is False, "Browser should not launch when scale is invalid"
    captured = capsys.readouterr().out
    assert "Scale must be one of" in captured


@pytest.mark.parametrize(
    ("duration", "hold", "expected_fragment"),
    [(-0.1, 1.0, "duration"), (1.0, -0.5, "hold")],
)
def test_cli_animate_when_timing_invalid_then_aborts_before_launch(
    monkeypatch,
    tmp_path: Path,
    capsys,
    duration: float,
    hold: float,
    expected_fragment: str,
) -> None:
    instances: list[_StubBrowser] = []

    def _factory(*args: Any, **kwargs: Any) -> _StubBrowser:
        browser = _StubBrowser(*args, **kwargs)
        instances.append(browser)
        return browser

    monkeypatch.setattr("vexy_stax.cli.VexyStaxBrowser", _factory)

    assets = tmp_path / "layers"
    _make_image(assets / "layer.png")

    cli = VexyStaxCLI()
    cli.animate(images=str(assets), duration=duration, hold=hold, backend="playwright")

    assert not instances, "Browser should not construct when timing is invalid"
    captured = capsys.readouterr().out
    assert expected_fragment in captured


def test_cli_animate_when_timing_valid_then_runs_browser_flow(
    monkeypatch, tmp_path: Path
) -> None:
    instances: list[_StubBrowser] = []

    def _factory(*args: Any, **kwargs: Any) -> _StubBrowser:
        browser = _StubBrowser(*args, **kwargs)
        instances.append(browser)
        return browser

    monkeypatch.setattr("vexy_stax.cli.VexyStaxBrowser", _factory)

    assets = tmp_path / "layers"
    _make_image(assets / "frame1.png")

    cli = VexyStaxCLI()
    cli.animate(images=str(assets), duration=2.5, hold=1.25, backend="playwright")

    assert instances, "Browser should initialize for valid timings"
    browser = instances[0]
    assert browser.launched is True
    assert browser.closed is True
    assert browser.loaded_images == [[str(assets / "frame1.png")]]
    assert browser.animation_calls == [
        {"duration": 2.5, "hold_time": 1.25, "easing": ""}
    ]


# Task 7: Test coverage for pygfx backend validation error paths


def test_cli_render_pygfx_when_file_missing_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    missing_path = tmp_path / "nonexistent.json"

    cli.render(images=str(missing_path), output="out.png", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Scene file not found" in captured
    assert "Check that the path is correct" in captured


def test_cli_render_pygfx_when_not_json_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    text_file = tmp_path / "scene.txt"
    text_file.write_text("not json")

    cli.render(images=str(text_file), output="out.png", backend="pygfx")

    captured = capsys.readouterr().out
    assert "requires JSON scene file" in captured
    assert "use --backend=playwright" in captured


def test_cli_render_pygfx_when_invalid_json_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    bad_json = tmp_path / "invalid.json"
    bad_json.write_text("{broken json")

    cli.render(images=str(bad_json), output="out.png", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Invalid JSON" in captured
    assert "Check the JSON syntax" in captured


def test_cli_render_pygfx_when_json_not_object_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    bad_json = tmp_path / "array.json"
    bad_json.write_text("[1, 2, 3]")

    cli.render(images=str(bad_json), output="out.png", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Scene JSON must be an object" in captured
    assert "got list" in captured


def test_cli_render_pygfx_when_missing_images_field_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    incomplete_json = tmp_path / "scene.json"
    incomplete_json.write_text('{"layers": []}')

    cli.render(images=str(incomplete_json), output="out.png", backend="pygfx")

    captured = capsys.readouterr().out
    assert "missing required 'images' field" in captured
    assert "exported with image data" in captured


def test_cli_render_when_invalid_backend_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    scene = tmp_path / "scene.json"
    scene.write_text('{"images": []}')

    cli.render(images=str(scene), output="out.png", backend="invalid")

    captured = capsys.readouterr().out
    assert "Invalid backend" in captured
    assert "playwright" in captured
    assert "pygfx" in captured


# Tests for animate command validation paths


def test_cli_animate_when_invalid_backend_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    scene = tmp_path / "scene.json"
    scene.write_text('{"images": []}')

    cli.animate(images=str(scene), backend="invalid")

    captured = capsys.readouterr().out
    assert "Invalid backend" in captured
    assert "playwright" in captured
    assert "pygfx" in captured


def test_cli_animate_pygfx_when_file_missing_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    missing_path = tmp_path / "nonexistent.json"

    cli.animate(images=str(missing_path), output="hero.mp4", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Scene file not found" in captured
    assert "Check that the path is correct" in captured


def test_cli_animate_pygfx_when_not_json_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    text_file = tmp_path / "scene.txt"
    text_file.write_text("not json")

    cli.animate(images=str(text_file), output="hero.mp4", backend="pygfx")

    captured = capsys.readouterr().out
    assert "requires JSON scene file" in captured
    assert "use --backend=playwright" in captured


def test_cli_animate_pygfx_when_invalid_json_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    bad_json = tmp_path / "invalid.json"
    bad_json.write_text("{broken json")

    cli.animate(images=str(bad_json), output="hero.mp4", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Invalid JSON" in captured
    assert "Check the JSON syntax" in captured


def test_cli_animate_pygfx_when_json_not_object_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    bad_json = tmp_path / "array.json"
    bad_json.write_text("[1, 2, 3]")

    cli.animate(images=str(bad_json), output="hero.mp4", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Scene JSON must be an object" in captured
    assert "got list" in captured


def test_cli_animate_pygfx_when_missing_images_field_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    incomplete_json = tmp_path / "scene.json"
    incomplete_json.write_text('{"layers": []}')

    cli.animate(images=str(incomplete_json), output="hero.mp4", backend="pygfx")

    captured = capsys.readouterr().out
    assert "missing required 'images' field" in captured
    assert "exported with image data" in captured


def test_cli_animate_pygfx_when_unsupported_format_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    scene = tmp_path / "scene.json"
    scene.write_text('{"images": []}')

    cli.animate(images=str(scene), output="hero.webm", backend="pygfx")

    captured = capsys.readouterr().out
    assert "Unsupported video format" in captured
    assert "Use .mp4 or .mov" in captured


# Tests for compare command


def test_cli_compare_when_test_image_missing_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    ref_path = tmp_path / "ref.png"
    _make_image(ref_path)

    cli.compare(test_image=str(tmp_path / "missing.png"), reference_image=str(ref_path))

    captured = capsys.readouterr().out
    assert "Test image not found" in captured


def test_cli_compare_when_reference_missing_then_reports_error(
    tmp_path: Path, capsys
) -> None:
    cli = VexyStaxCLI()
    test_path = tmp_path / "test.png"
    _make_image(test_path)

    cli.compare(
        test_image=str(test_path), reference_image=str(tmp_path / "missing.png")
    )

    captured = capsys.readouterr().out
    assert "Reference image not found" in captured


def test_cli_compare_when_identical_images_then_passes(tmp_path: Path, capsys) -> None:
    cli = VexyStaxCLI()
    img_path = tmp_path / "img.png"
    _make_image(img_path)

    cli.compare(test_image=str(img_path), reference_image=str(img_path))

    captured = capsys.readouterr().out
    assert "PASS" in captured
    assert "MAE:" in captured
    assert "Pixel match:" in captured


def test_cli_compare_when_diff_output_then_saves_file(tmp_path: Path) -> None:
    cli = VexyStaxCLI()
    img_path = tmp_path / "img.png"
    diff_path = tmp_path / "diff.png"
    _make_image(img_path)

    cli.compare(
        test_image=str(img_path),
        reference_image=str(img_path),
        diff_output=str(diff_path),
    )

    assert diff_path.exists(), "Diff image should be created"
