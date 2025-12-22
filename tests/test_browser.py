# this_file: tests/test_browser.py
"""Tests for the Playwright browser adapter."""

from __future__ import annotations

from pathlib import Path

from vexy_stax.browser import VexyStaxBrowser


class _DownloadStub:
    def __init__(self) -> None:
        self.saved: list[Path] = []

    def save_as(self, target: str) -> None:
        path = Path(target)
        if not path.parent.exists():
            raise FileNotFoundError("parent missing")
        self.saved.append(path)

    def path(self) -> Path:
        return Path("/tmp/dummy.png")


class _DownloadContext:
    def __init__(self, download: _DownloadStub) -> None:
        self.value = download

    def __enter__(self) -> _DownloadContext:
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class _PageStub:
    def __init__(self, *, image_count: int, download: _DownloadStub) -> None:
        self._image_count = image_count
        self._download = download
        self.evaluate_calls: list[tuple[str, tuple, dict]] = []

    def evaluate(self, script: str, *args, **kwargs):
        self.evaluate_calls.append((script, args, kwargs))
        if script == "window.vexyStax.getStats()":
            return {"imageCount": self._image_count}
        if script.startswith("("):
            return None
        raise AssertionError(f"Unexpected evaluate call: {script}")

    def expect_download(self, timeout: int = 10000) -> _DownloadContext:
        return _DownloadContext(self._download)


def test_export_png_when_output_parent_missing_then_creates_directory(
    tmp_path: Path,
) -> None:
    browser = VexyStaxBrowser()
    download = _DownloadStub()
    browser.page = _PageStub(image_count=1, download=download)

    target = tmp_path / "nested" / "result.png"
    assert not target.parent.exists()

    result = browser.export_png(scale=1, output_path=str(target))

    assert result == b"", "export should return empty bytes when saving to disk"
    assert target.parent.exists(), "Parent directory should be created automatically"
    assert download.saved == [target], "Download should persist to requested path"
    assert any(
        call[0] == "window.vexyStax.getStats()" for call in browser.page.evaluate_calls
    ), "Should query page stats before exporting"
