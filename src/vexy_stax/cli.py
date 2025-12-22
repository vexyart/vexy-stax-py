#!/usr/bin/env python3
# this_file: vexy-stax-py/src/vexy_stax/cli.py

"""Fire CLI for vexy-stax browser automation"""

import fire
import time
from pathlib import Path

from .browser import VexyStaxBrowser
from .config import validate_animation_timing, validate_scale

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")

VALID_BACKENDS = ("playwright", "pygfx")
DEFAULT_BACKEND = "pygfx"  # Default: headless GPU rendering (fast, no browser)


def _validate_backend(backend: str) -> str:
    """Validate backend choice and return normalized value."""
    backend = backend.lower()
    if backend not in VALID_BACKENDS:
        allowed = ", ".join(VALID_BACKENDS)
        raise ValueError(f"Invalid backend '{backend}'. Choose from: {allowed}")
    return backend


class VexyStaxCLI:
    """
    Vexy Stax CLI - Render layered image stacks with depth and animation

    Supports two rendering backends:
    - pygfx: Headless GPU rendering (fast, no browser needed)
    - playwright: Browser automation (pixel-perfect match to web UI)
    """

    def version(self):
        """
        Show version and backend capabilities

        Example:
            vexy-stax version
        """
        from . import __version__

        print(f"vexy-stax {__version__}")
        print("\nBackends:")
        print("  ✅ pygfx     - Headless GPU rendering (requires JSON scenes)")
        print("  ✅ playwright - Browser automation (requires dev server)")
        print("\nFor help: vexy-stax --help")

    def doctor(self):
        """
        Diagnose GPU capabilities for pygfx rendering

        Status: ✅ Working

        Checks if your system has a compatible GPU for headless rendering.
        Provides platform-specific guidance if GPU is not available.

        Example:
            vexy-stax doctor
        """
        from .gpu_doctor import diagnose_gpu, format_diagnostics

        diag = diagnose_gpu()
        print(format_diagnostics(diag))

    def compare(
        self,
        test_image: str,
        reference_image: str,
        diff_output: str | None = None,
        tolerance: int = 10,
    ):
        """
        Compare two images and report visual similarity

        Status: ✅ Working

        Compares a test image against a reference image using MAE
        and pixel match metrics. Useful for validating render output.

        Args:
            test_image: Path to test image (e.g., pygfx render)
            reference_image: Path to reference image (e.g., JS render)
            diff_output: Optional path to save difference visualization
            tolerance: Per-channel tolerance for pixel matching (0-255, default: 10)

        Examples:
            # Basic comparison
            vexy-stax compare pygfx_render.png js_reference.png

            # Save diff visualization
            vexy-stax compare pygfx_render.png js_reference.png --diff-output=diff.png
        """
        from pathlib import Path
        from .image_comparison import compare_images, save_diff_image

        test_path = Path(test_image)
        ref_path = Path(reference_image)

        # Validate paths
        if not test_path.is_file():
            print(f"Error: Test image not found: {test_image}")
            return

        if not ref_path.is_file():
            print(f"Error: Reference image not found: {reference_image}")
            return

        print(f"Comparing: {test_path.name} vs {ref_path.name}")

        try:
            result = compare_images(
                test_path,
                ref_path,
                tolerance=tolerance,
                generate_diff=diff_output is not None,
            )

            # Display results
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"\n{status}")
            print(f"  MAE:         {result.mae:.2f} (threshold: <35)")
            print(f"  Pixel match: {result.pixel_match_ratio:.1%} (threshold: >35%)")
            print(f"  Max diff:    {result.max_diff}")

            # Save diff image if requested
            if diff_output:
                diff_path = Path(diff_output)
                save_diff_image(result, diff_path)
                print(f"\n  Diff saved: {diff_path}")

        except ValueError as exc:
            print(f"Error: {exc}")

    def _load_images(self, browser: VexyStaxBrowser, images: str) -> bool:
        """
        Load images from folder or JSON config

        Args:
            browser: VexyStaxBrowser instance
            images: Path to folder with images or JSON config file

        Returns:
            True if images loaded successfully, False otherwise
        """
        image_path = Path(images)

        if image_path.is_file() and image_path.suffix.lower() == ".json":
            browser.load_config(str(image_path))
            return True
        elif image_path.is_dir():
            image_files = sorted(
                (
                    entry
                    for entry in image_path.iterdir()
                    if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES
                ),
                key=lambda path: path.name.lower(),
            )

            if not image_files:
                allowed = ", ".join(suffix.upper() for suffix in IMAGE_SUFFIXES)
                print(f"Error: No image files ({allowed}) found in {images}")
                return False

            browser.load_images([str(f) for f in image_files])
            return True
        else:
            print(f"Error: {images} is not a valid folder or JSON file")
            return False

    def launch(
        self,
        images: str | None = None,
        url: str = "http://localhost:5173/vexy-stax-js/",
        headless: bool = False,
    ):
        """
        Launch web app and load images (Playwright backend)

        Status: ✅ Working - requires dev server running on localhost

        Args:
            images: Path to folder with images or JSON config file
            url: URL of vexy-stax-js app (default: local dev server)
            headless: Run browser in headless mode

        Example:
            vexy-stax launch images=./layers --headless
        """
        browser = VexyStaxBrowser(url=url, headless=headless)

        try:
            browser.launch()

            if images:
                if not self._load_images(browser, images):
                    return

            print("✓ Browser launched")
            if not headless:
                input("Press Enter to close browser...")

        finally:
            browser.close()

    def animate(
        self,
        images: str,
        output: str = "animation.mp4",
        url: str = "http://localhost:5173/vexy-stax-js/",
        duration: float = 1.5,
        hold: float = 1.0,
        backend: str = DEFAULT_BACKEND,
        width: int = 800,
        height: int = 600,
        fps: int = 30,
        require_gpu: bool = False,
    ):
        """
        Animate hero-shot and export video

        Status: ✅ Working (pygfx backend), 🚧 Playwright backend preview only

        Args:
            images: Path to folder with images or JSON config file
            output: Output video file path (.mp4 or .mov)
            url: URL of vexy-stax-js app (playwright backend only)
            duration: Animation duration in seconds (must be > 0)
            hold: Hold time at hero position in seconds (must be >= 0)
            backend: Rendering backend (default: 'pygfx')
                - 'pygfx': Headless GPU rendering with video export (JSON only)
                - 'playwright': Browser preview only (no recording yet)
            width: Canvas width in pixels (pygfx backend only, default: 800)
            height: Canvas height in pixels (pygfx backend only, default: 600)
            fps: Frames per second (pygfx backend only, default: 30)
            require_gpu: Fail if hardware GPU not available (rejects software rendering)

        Examples:
            # Pygfx backend (exports video):
            vexy-stax animate images=scene.json output=hero.mp4 --backend=pygfx --width=1920 --height=1080

            # Require hardware GPU (fail on software rendering):
            vexy-stax animate images=scene.json output=hero.mp4 --require-gpu

            # Playwright backend (preview only):
            vexy-stax animate images=./layers --backend=playwright
        """
        try:
            validate_animation_timing(fps=fps, duration=duration, hold=hold)
            backend = _validate_backend(backend)
        except ValueError as exc:
            print(f"Error: {exc}")
            return

        if backend == "pygfx":
            self._animate_pygfx(
                images, output, width, height, duration, hold, fps, require_gpu
            )
        else:
            self._animate_playwright(images, output, url, duration, hold)

    def _animate_pygfx(
        self,
        images: str,
        output: str,
        width: int,
        height: int,
        duration: float,
        hold: float,
        fps: int,
        require_gpu: bool = False,
    ):
        """Render hero-shot animation using pygfx headless renderer."""
        from .config import AnimationDefaults
        from .render_pipeline import pygfx_render_video
        from .loader import LoaderError
        from .renderer.context import GPUUnavailableError
        from .renderer.export import VideoExportError
        from .gpu_doctor import check_gpu_requirements, SoftwareRenderingError
        import json

        # Check GPU requirements upfront
        if require_gpu:
            try:
                check_gpu_requirements(require_hardware=True)
            except SoftwareRenderingError as exc:
                print(f"Error: {exc}")
                return
            except RuntimeError as exc:
                print(f"Error: {exc}")
                return

        image_path = Path(images)

        # Validate: pygfx backend requires JSON config
        if not image_path.is_file():
            print(
                f"Error: Scene file not found: {images}\n"
                f"Fix: Check that the path is correct and the file exists"
            )
            return

        if image_path.suffix.lower() != ".json":
            print(
                f"Error: pygfx backend requires JSON scene file, got: {images}\n"
                f"Fix: Use vexy-stax-js to export a scene JSON first, or use --backend=playwright for image directories"
            )
            return

        # Validate: JSON is parseable and has required fields
        try:
            with open(image_path) as f:
                scene_data = json.load(f)
        except json.JSONDecodeError as exc:
            print(
                f"Error: Invalid JSON in scene file: {exc.msg} at line {exc.lineno}\n"
                f"Fix: Check the JSON syntax in {image_path}"
            )
            return
        except Exception as exc:
            print(f"Error: Cannot read scene file: {exc}\nFix: Check file permissions")
            return

        if not isinstance(scene_data, dict):
            print(
                f"Error: Scene JSON must be an object, got {type(scene_data).__name__}\n"
                f"Fix: Ensure the JSON exports from vexy-stax-js correctly"
            )
            return

        if "images" not in scene_data:
            print(
                "Error: Scene JSON missing required 'images' field\n"
                "Fix: Ensure the scene was exported with image data from vexy-stax-js"
            )
            return

        # Validate output format
        output_path = Path(output)
        if output_path.suffix.lower() not in (".mp4", ".mov"):
            print(
                f"Error: Unsupported video format: {output_path.suffix}\n"
                f"Fix: Use .mp4 or .mov extension"
            )
            return

        animation = AnimationDefaults(fps=fps, duration=duration, hold=hold)
        total_frames = int((duration + hold) * fps)

        print(f"⏵ Rendering hero-shot with pygfx ({width}x{height} @ {fps}fps)...")
        print(f"  Duration: {duration}s + {hold}s hold = {total_frames} frames")
        start_time = time.time()

        try:
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("{task.completed}/{task.total} frames"),
                transient=True,
            ) as progress:
                task = progress.add_task("Rendering", total=total_frames)

                def on_progress(current: int, total: int) -> None:
                    progress.update(task, completed=current)

                result = pygfx_render_video(
                    scene_json=image_path,
                    output_path=output,
                    width=width,
                    height=height,
                    animation=animation,
                    on_progress=on_progress,
                )

            elapsed = time.time() - start_time
            print(f"✓ Video exported to {result.path} ({elapsed:.2f}s)")
            print(f"  Codec: {result.codec}, Frames: {result.frames}")
        except LoaderError as exc:
            print(
                f"Error: Scene loading failed: {exc}\n"
                f"Fix: Check that the scene JSON is from vexy-stax-js and contains valid image data"
            )
        except GPUUnavailableError as exc:
            print(
                f"Error: GPU not available: {exc}\n"
                f"Fix: Ensure your system has GPU drivers installed:\n"
                f"  - macOS: Requires macOS 10.13+ (Metal support)\n"
                f"  - Linux: Install vulkan-loader and GPU drivers\n"
                f"  - Windows: Install DirectX 12 or Vulkan drivers"
            )
        except VideoExportError as exc:
            print(
                f"Error: Video encoding failed: {exc}\n"
                f"Fix: Ensure FFmpeg is installed with H.264/ProRes codecs"
            )
        except Exception as exc:
            print(f"Error: Animation failed: {exc}")
            import traceback

            traceback.print_exc()

    def _animate_playwright(
        self,
        images: str,
        output: str,
        url: str,
        duration: float,
        hold: float,
    ):
        """Preview hero-shot animation using Playwright browser automation."""
        browser = VexyStaxBrowser(url=url, headless=True)

        try:
            browser.launch()

            # Load images
            if not self._load_images(browser, images):
                return

            print("✓ Images loaded")

            # Play animation (preview only)
            print(f"⏵ Playing animation (duration: {duration}s, hold: {hold}s)...")
            browser.play_animation(duration=duration, hold_time=hold)

            print("✓ Animation preview complete")
            print("Note: Playwright backend does not export video yet")
            print("Tip: Use --backend=pygfx for video export")

        finally:
            browser.close()

    def render(
        self,
        images: str,
        output: str,
        url: str = "http://localhost:5173/vexy-stax-js/",
        scale: int = 1,
        backend: str = DEFAULT_BACKEND,
        width: int = 800,
        height: int = 600,
        require_gpu: bool = False,
    ):
        """
        Render composition to PNG file

        Status: ✅ Working - both backends functional

        Args:
            images: Path to folder with images or JSON config file
            output: Output PNG file path
            url: URL of vexy-stax-js app (playwright backend only)
            scale: Resolution scale (1, 2, or 4)
            backend: Rendering backend (default: 'pygfx')
                - 'pygfx': Headless GPU rendering, fast, no server needed (JSON only)
                - 'playwright': Browser automation, pixel-perfect, requires dev server
            width: Canvas width in pixels (pygfx backend only, default: 800)
            height: Canvas height in pixels (pygfx backend only, default: 600)
            require_gpu: Fail if hardware GPU not available (rejects software rendering)

        Examples:
            # Pygfx backend (fast, headless):
            vexy-stax render images=scene.json output=out.png --backend=pygfx --width=1920 --height=1080

            # Require hardware GPU:
            vexy-stax render images=scene.json output=out.png --require-gpu

            # Playwright backend (pixel-perfect):
            vexy-stax render images=./layers output=out.png --backend=playwright --scale=2
        """
        try:
            validate_scale(scale)
            backend = _validate_backend(backend)
        except ValueError as exc:
            print(f"Error: {exc}")
            return

        # Route to appropriate backend
        if backend == "pygfx":
            self._render_pygfx(images, output, width, height, scale, require_gpu)
        else:
            self._render_playwright(images, output, url, scale)

    def _render_pygfx(
        self,
        images: str,
        output: str,
        width: int,
        height: int,
        scale: int,
        require_gpu: bool = False,
    ):
        """Render using pygfx headless renderer."""
        from .render_pipeline import pygfx_render_png
        from .loader import LoaderError
        from .renderer.context import GPUUnavailableError
        from .gpu_doctor import check_gpu_requirements, SoftwareRenderingError
        import json

        # Check GPU requirements upfront
        if require_gpu:
            try:
                check_gpu_requirements(require_hardware=True)
            except SoftwareRenderingError as exc:
                print(f"Error: {exc}")
                return
            except RuntimeError as exc:
                print(f"Error: {exc}")
                return

        image_path = Path(images)

        # Validate: pygfx backend requires JSON config
        if not image_path.is_file():
            print(
                f"Error: Scene file not found: {images}\n"
                f"Fix: Check that the path is correct and the file exists"
            )
            return

        if image_path.suffix.lower() != ".json":
            print(
                f"Error: pygfx backend requires JSON scene file, got: {images}\n"
                f"Fix: Use vexy-stax-js to export a scene JSON first, or use --backend=playwright for image directories"
            )
            return

        # Validate: JSON is parseable
        try:
            with open(image_path) as f:
                scene_data = json.load(f)
        except json.JSONDecodeError as exc:
            print(
                f"Error: Invalid JSON in scene file: {exc.msg} at line {exc.lineno}\n"
                f"Fix: Check the JSON syntax in {image_path}"
            )
            return
        except Exception as exc:
            print(f"Error: Cannot read scene file: {exc}\nFix: Check file permissions")
            return

        # Validate: JSON has required fields
        if not isinstance(scene_data, dict):
            print(
                f"Error: Scene JSON must be an object, got {type(scene_data).__name__}\n"
                f"Fix: Ensure the JSON exports from vexy-stax-js correctly"
            )
            return

        if "images" not in scene_data:
            print(
                "Error: Scene JSON missing required 'images' field\n"
                "Fix: Ensure the scene was exported with image data from vexy-stax-js"
            )
            return

        print(f"⏵ Rendering with pygfx backend ({width}x{height} @ {scale}x)...")
        start_time = time.time()

        try:
            result = pygfx_render_png(
                scene_json=image_path,
                output_path=output,
                width=width,
                height=height,
                scale=scale,
            )
            elapsed = time.time() - start_time
            print(f"✓ PNG exported to {result.path} ({elapsed:.2f}s)")
        except LoaderError as exc:
            print(
                f"Error: Scene loading failed: {exc}\n"
                f"Fix: Check that the scene JSON is from vexy-stax-js and contains valid image data"
            )
        except GPUUnavailableError as exc:
            print(
                f"Error: GPU not available: {exc}\n"
                f"Fix: Ensure your system has GPU drivers installed:\n"
                f"  - macOS: Requires macOS 10.13+ (Metal support)\n"
                f"  - Linux: Install vulkan-loader and GPU drivers\n"
                f"  - Windows: Install DirectX 12 or Vulkan drivers"
            )
        except Exception as exc:
            print(f"Error: Rendering failed: {exc}")
            import traceback

            traceback.print_exc()

    def _render_playwright(
        self,
        images: str,
        output: str,
        url: str,
        scale: int,
    ):
        """Render using Playwright browser automation."""

        browser = VexyStaxBrowser(url=url, headless=True)
        start_time = time.time()

        try:
            browser.launch()

            # Load images
            if not self._load_images(browser, images):
                return

            print("✓ Images loaded")

            # Export PNG
            print(f"⏵ Exporting PNG at {scale}x resolution...")
            browser.export_png(scale=scale, output_path=output)

            elapsed = time.time() - start_time
            print(f"✓ PNG exported to {output} ({elapsed:.2f}s)")

        finally:
            browser.close()


def main():
    """Entry point for vexy-stax CLI"""
    fire.Fire(VexyStaxCLI)


if __name__ == "__main__":
    main()
