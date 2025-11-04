#!/usr/bin/env python3
# this_file: vexy-stax-py/src/vexy_stax/cli.py

"""Fire CLI for vexy-stax browser automation"""

import fire
from pathlib import Path
from .browser import VexyStaxBrowser


class VexyStaxCLI:
    """CLI for controlling Vexy Stax web app via Playwright"""

    def launch(self,
               images: str | None = None,
               url: str = "http://localhost:5173/vexy-stax-js/",
               headless: bool = False):
        """
        Launch web app and load images

        Args:
            images: Path to folder with images or JSON config file
            url: URL of vexy-stax-js app (default: local dev server)
            headless: Run browser in headless mode
        """
        browser = VexyStaxBrowser(url=url, headless=headless)

        try:
            browser.launch()

            if images:
                image_path = Path(images)
                if image_path.is_file() and image_path.suffix == '.json':
                    browser.load_config(str(image_path))
                elif image_path.is_dir():
                    image_files = list(image_path.glob('*.png'))
                    browser.load_images([str(f) for f in image_files])
                else:
                    print(f"Error: {images} is not a valid folder or JSON file")
                    return

            print("✓ Browser launched")
            if not headless:
                input("Press Enter to close browser...")

        finally:
            browser.close()

    def animate(self,
                images: str,
                output: str = "animation.webm",
                url: str = "http://localhost:5173/vexy-stax-js/",
                duration: float = 1.5,
                hold: float = 1.0):
        """
        Animate and record video

        Args:
            images: Path to folder with images or JSON config file
            output: Output video file path
            url: URL of vexy-stax-js app
            duration: Animation duration in seconds
            hold: Hold time at hero position
        """
        browser = VexyStaxBrowser(url=url, headless=True)

        try:
            browser.launch()

            # Load images
            image_path = Path(images)
            if image_path.is_file() and image_path.suffix == '.json':
                browser.load_config(str(image_path))
            elif image_path.is_dir():
                image_files = list(image_path.glob('*.png'))
                browser.load_images([str(f) for f in image_files])
            else:
                print(f"Error: {images} is not a valid folder or JSON file")
                return

            print("✓ Images loaded")

            # Play animation and record
            print(f"⏵ Playing animation (duration: {duration}s, hold: {hold}s)...")
            browser.play_animation(duration=duration, hold_time=hold)

            # TODO: Implement video recording
            print(f"✓ Animation complete (recording not yet implemented)")
            print(f"TODO: Save to {output}")

        finally:
            browser.close()


def main():
    """Entry point for vexy-stax CLI"""
    fire.Fire(VexyStaxCLI)


if __name__ == '__main__':
    main()
