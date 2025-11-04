#!/usr/bin/env python3
# this_file: vexy-stax-py/src/vexy_stax/browser.py

"""Playwright browser automation for Vexy Stax web app"""

from playwright.sync_api import sync_playwright, Page, Browser
import json
from pathlib import Path


class VexyStaxBrowser:
    """Control Vexy Stax web app via Playwright"""

    def __init__(self, url: str = "http://localhost:5173/vexy-stax-js/", headless: bool = False):
        self.url = url
        self.headless = headless
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def launch(self):
        """Launch browser and navigate to app"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
            self.page.goto(self.url, timeout=5000)
            self.page.wait_for_load_state("networkidle")
        except Exception as e:
            self.close()
            if "net::ERR_CONNECTION_REFUSED" in str(e) or "Timeout" in str(e):
                raise RuntimeError(
                    f"Cannot connect to {self.url}\n"
                    f"Make sure the dev server is running:\n"
                    f"  cd vexy-stax-js && npm run dev"
                ) from e
            raise

    def close(self):
        """Close browser"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def load_images(self, image_paths: list[str]):
        """
        Load images into the web app

        Args:
            image_paths: List of paths to PNG files

        Raises:
            RuntimeError: If browser not launched or files don't exist
        """
        if not self.page:
            raise RuntimeError("load_images: Browser not launched. Call launch() first.")

        # Validate all files exist before uploading
        for path in image_paths:
            if not Path(path).exists():
                raise RuntimeError(
                    f"Image file not found: {path}\n"
                    f"Make sure the file exists and the path is correct."
                )

        # Use file input to upload images
        file_input = self.page.locator('input[type="file"]')
        file_input.set_input_files(image_paths)

        # Wait for images to load by polling imageStack count
        expected_count = len(image_paths)
        max_wait = 5000  # 5 seconds max
        poll_interval = 100  # Check every 100ms
        elapsed = 0

        while elapsed < max_wait:
            stats = self.page.evaluate("window.vexyStax.getStats()")
            if stats and stats.get('imageCount', 0) >= expected_count:
                # All images loaded
                return
            self.page.wait_for_timeout(poll_interval)
            elapsed += poll_interval

        # Timeout - check what we got
        final_stats = self.page.evaluate("window.vexyStax.getStats()")
        loaded_count = final_stats.get('imageCount', 0) if final_stats else 0
        raise RuntimeError(
            f"Timeout waiting for images to load\n"
            f"Expected {expected_count} images, but only {loaded_count} loaded.\n"
            f"Images may be too large or have failed to load."
        )

    def load_config(self, config_path: str):
        """
        Load configuration JSON file

        Args:
            config_path: Path to JSON config file with images and settings

        Raises:
            RuntimeError: If browser not launched, file not found, or invalid JSON
        """
        if not self.page:
            raise RuntimeError("load_config: Browser not launched. Call launch() first.")

        # Read JSON file with proper error handling
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(
                f"Config file not found: {config_path}\n"
                f"Make sure the file exists and the path is correct."
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON in config file: {config_path}\n"
                f"Error at line {e.lineno}, column {e.colno}: {e.msg}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to read config file: {config_path}\n"
                f"Error: {str(e)}"
            ) from e

        # Pass config to loadConfig API method (waits for promise to resolve)
        # The loadConfig function now returns a promise that resolves when all images are loaded
        self.page.evaluate("(config) => window.vexyStax.loadConfig(config)", config)

    def play_animation(self, duration: float = 1.5, hold_time: float = 1.0, easing: str = "power2.inOut"):
        """
        Play hero shot animation

        Args:
            duration: Animation duration in seconds
            hold_time: Hold time at hero position
            easing: GSAP easing function
        """
        if not self.page:
            raise RuntimeError("play_animation: Browser not launched. Call launch() first.")

        # Use debug API to play animation
        animation_config = {
            "duration": duration,
            "holdTime": hold_time,
            "easing": easing
        }

        # Call animation via JavaScript - Playwright waits for promise to resolve
        # The JS playAnimation() is async and returns a promise
        self.page.evaluate("(config) => window.vexyStax.playAnimation(config)", animation_config)

    def export_png(self, scale: int = 1, output_path: str | None = None) -> bytes:
        """
        Export current view as PNG

        Args:
            scale: Resolution scale (1x, 2x, or 4x)
            output_path: Optional path to save PNG file

        Returns:
            PNG bytes

        Raises:
            RuntimeError: If download fails or times out
            ValueError: If scale is not 1, 2, or 4
        """
        if not self.page:
            raise RuntimeError("export_png: Browser not launched. Call launch() first.")

        # Validate scale parameter
        if scale not in (1, 2, 4):
            raise ValueError(
                f"Invalid scale: {scale}\n"
                f"Scale must be 1, 2, or 4 (for 1x, 2x, or 4x resolution)"
            )

        # Verify images are loaded before attempting export
        stats = self.page.evaluate("window.vexyStax.getStats()")
        if not stats or stats.get('imageCount', 0) == 0:
            raise RuntimeError(
                "export_png: No images loaded in the app.\n"
                "Load images with load_images() or load_config() first."
            )

        # Trigger export via debug API (safe parameter passing)
        self.page.evaluate("(scale) => window.vexyStax.exportPNG(scale)", scale)

        # Wait for download with timeout
        try:
            with self.page.expect_download(timeout=10000) as download_info:
                download = download_info.value
        except Exception as e:
            raise RuntimeError(
                f"Failed to download PNG export: {str(e)}\n"
                f"Make sure images are loaded in the app."
            ) from e

        # Verify download succeeded
        if not download:
            raise RuntimeError("Download failed - no file received")

        try:
            if output_path:
                download.save_as(output_path)
                return b''
            else:
                return download.path().read_bytes()
        except Exception as e:
            raise RuntimeError(f"Failed to save downloaded PNG: {str(e)}") from e

    def get_stats(self) -> dict:
        """
        Get current stats from web app

        Returns:
            Dictionary with imageCount, memoryUsage, and other stats

        Raises:
            RuntimeError: If browser not launched
        """
        if not self.page:
            raise RuntimeError("get_stats: Browser not launched. Call launch() first.")

        return self.page.evaluate("window.vexyStax.getStats()")
