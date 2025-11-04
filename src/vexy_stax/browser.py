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
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

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

        # Call animation via JavaScript
        self.page.evaluate(f"""
            window.vexyStax.playAnimation({{
                duration: {duration},
                holdTime: {hold_time},
                easing: '{easing}'
            }})
        """)

        # Wait for animation to complete (duration * 2 + hold_time + buffer)
        total_time = (duration * 2 + hold_time + 0.5) * 1000
        self.page.wait_for_timeout(int(total_time))

    def export_png(self, scale: int = 1, output_path: str | None = None) -> bytes:
        """
        Export current view as PNG

        Args:
            scale: Resolution scale (1x, 2x, 4x)
            output_path: Optional path to save PNG file

        Returns:
            PNG bytes
        """
        if not self.page:
            raise RuntimeError("Browser not launched")

        # Trigger export via debug API
        self.page.evaluate(f"window.vexyStax.exportPNG({scale})")

        # Wait for download
        with self.page.expect_download() as download_info:
            download = download_info.value

        if output_path:
            download.save_as(output_path)
            return b''
        else:
            return download.path().read_bytes()

    def get_stats(self) -> dict:
        """Get current stats from web app"""
        if not self.page:
            raise RuntimeError("Browser not launched")

        return self.page.evaluate("window.vexyStax.getStats()")
