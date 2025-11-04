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
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

        # Use file input to upload images
        file_input = self.page.locator('input[type="file"]')
        file_input.set_input_files(image_paths)

        # Wait for images to load
        self.page.wait_for_timeout(1000)

    def load_config(self, config_path: str):
        """
        Load configuration JSON file

        Args:
            config_path: Path to JSON config file with images and settings
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

        # Read JSON file
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Pass config to loadConfig API method
        self.page.evaluate("(config) => window.vexyStax.loadConfig(config)", config)

        # Wait for processing
        self.page.wait_for_timeout(1000)

    def play_animation(self, duration: float = 1.5, hold_time: float = 1.0, easing: str = "power2.inOut"):
        """
        Play hero shot animation

        Args:
            duration: Animation duration in seconds
            hold_time: Hold time at hero position
            easing: GSAP easing function
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

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
            scale: Resolution scale (1x, 2x, 4x)
            output_path: Optional path to save PNG file

        Returns:
            PNG bytes

        Raises:
            RuntimeError: If download fails or times out
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

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
        """Get current stats from web app"""
        if not self.page:
            raise RuntimeError("Browser not launched")

        return self.page.evaluate("window.vexyStax.getStats()")
