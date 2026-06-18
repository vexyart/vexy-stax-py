# this_file: src/vexy_stax/cli.py
"""fire + rich CLI for vexy-stax (SPEC.md §5.2)."""

from __future__ import annotations

import os
import re
from pathlib import Path

import fire
from rich.console import Console

from vexy_stax.engines import available_engines, get_engine
from vexy_stax.images import overlay_images, read_images
from vexy_stax.scene import (
    Caption,
    Floor,
    Scene,
    Size,
    Slide,
    Transition,
    View,
    load_scene,
)

console = Console()

# Defaults per SPEC.md §5.2: still -> pygfx (fast), video -> blender (quality).
_DEFAULT_IMAGE_ENGINE = "pygfx"
_DEFAULT_VIDEO_ENGINE = "blender"


class Stax:
    """Render layered PNGs as 3D glass plates from a shared JSON scene."""

    def render(
        self,
        scene: str,
        view: View = "expanded",
        engine: str | None = None,
        out: str = "out.png",
    ) -> None:
        """Render a single still of SCENE in VIEW (expanded|compact)."""
        sc = load_scene(scene)
        name = engine or _DEFAULT_IMAGE_ENGINE
        self._run(name, lambda e: e.render_image(sc, view, Path(out)), out)

    def video(
        self,
        scene: str,
        engine: str | None = None,
        out: str = "out.mp4",
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        frames: int | None = None,
        first_hold: int | None = None,
        last_hold: int | None = None,
    ) -> None:
        """Render SCENE's transition to a video file.

        Video params come from the scene's ``video`` section (issue 335 §3); any of
        ``width``/``height``/``fps``/``frames``/``first_hold``/``last_hold`` given here override
        the scene values for this render (``first_hold``/``last_hold`` are the held first/last
        still-frame counts, default 10 each).
        """
        sc = load_scene(scene)
        if width is not None:
            sc.video.width = width
        if height is not None:
            sc.video.height = height
        if fps is not None:
            sc.video.fps = fps
        if frames is not None:
            sc.video.frames = frames
        if first_hold is not None:
            sc.video.first_hold = first_hold
        if last_hold is not None:
            sc.video.last_hold = last_hold
        name = engine or _DEFAULT_VIDEO_ENGINE
        self._run(name, lambda e: e.render_video(sc, Path(out)), out)

    def overlay(self, scene: str, out: str = "flat.png") -> None:
        """Pure-Pillow flat composite of SCENE's slides (no 3D engine)."""
        sc = load_scene(scene)
        infos = read_images([s.src for s in sc.slides])
        overlay_images(infos, out)
        console.print(f"[green]Wrote[/green] {out}")

    def engines(self) -> None:
        """List engines whose dependencies are available."""
        names = available_engines()
        if names:
            console.print("[bold]Available engines:[/bold] " + ", ".join(names))
        else:
            console.print("[yellow]No engines available.[/yellow] Install blender, pygfx, or playwright.")

    def dir2scene(
        self,
        directory: str,
        out: str = "scene.json",
        view: View = "expanded",
        width: int | None = None,
        height: int | None = None,
        gap: float | None = None,
        distance: str | float = "100%",
        angle: float = 60.0,
        elevation: float = 0.0,
        fov: float = 39.6,
        background: str = "#ffffff",
        floor_color: str = "#f2f2f2",
        floor_opacity: float = 1.0,
        floor_reflectivity: float = 0.5,
        transition_kind: str | None = None,
        transition_duration: float = 3.0,
        transition_wait: float = 1.0,
        transition_fps: int = 30,
        transition_easing: str = "easeInOutCubic",
        reverse: bool = False,
        captions: bool = True,
        juicy: bool = False,
    ) -> None:
        """Generate a scene JSON from a directory of images.

        Scans the directory for image files (PNG, JPG, JPEG, WEBP), sorts them
        naturally, auto-detects scene dimensions, and writes a valid scene JSON.
        """
        path = Path(directory)
        if not path.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        extensions = {".png", ".jpg", ".jpeg", ".webp"}
        image_files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in extensions]
        if not image_files:
            raise FileNotFoundError(f"No images found in directory: {directory}")

        # Natural sort so 2.png comes before 10.png
        def natural_sort_key(p: Path):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", p.name)]

        image_files.sort(key=natural_sort_key)
        if reverse:
            image_files.reverse()

        infos = read_images(image_files)

        out_path = Path(out).resolve()
        if out_path.is_dir():
            out_path = out_path / "scene.json"

        json_dir = out_path.parent
        json_dir.mkdir(parents=True, exist_ok=True)

        detected_width = width or infos[0]["width"]
        detected_height = height or infos[0]["height"]

        if gap is None:
            # Smart default gap: ~38% of scene width, rounded to a clean integer
            gap = float(int(detected_width * 0.38))

        # Find common prefix to clean up captions
        filenames = [f.name for f in image_files]
        prefix = ""
        if len(filenames) > 1:
            s1 = min(filenames)
            s2 = max(filenames)
            for i, c in enumerate(s1):
                if i >= len(s2) or c != s2[i]:
                    prefix = s1[:i]
                    break
            else:
                prefix = s1

        slides = []
        for info, img_file in zip(infos, image_files, strict=True):
            # Compute relative path from scene JSON parent to the image file
            rel_src = os.path.relpath(info["path"], json_dir)

            caption_obj = None
            if captions:
                # Strip prefix, strip numbers/symbols, title-case
                name = img_file.name
                if prefix and name.startswith(prefix):
                    name = name[len(prefix) :]
                name = Path(name).stem
                name = re.sub(r"^[\d\s\-_]+", "", name)
                name = re.sub(r"[\d\s\-_]+$", "", name)
                name = re.sub(r"[\-_]", " ", name)
                name = re.sub(r"\s+", " ", name).strip()
                caption_text = name.title() or "Slide"
                caption_obj = Caption(text=caption_text, show_in="expanded")

            slides.append(
                Slide(
                    src=rel_src,
                    opacity=1.0,
                    caption=caption_obj,
                )
            )

        from vexy_stax.scene import Camera

        camera = Camera(
            gap=gap,
            distance=distance,
            angle=angle,
            elevation=elevation,
            fov=fov,
        )

        floor = Floor(
            color=floor_color,
            opacity=floor_opacity,
            reflectivity=floor_reflectivity,
        )

        transition = None
        if transition_kind is not None:
            transition = Transition(
                kind=transition_kind,  # type: ignore[arg-type]
                duration=transition_duration,
                wait=transition_wait,
                fps=transition_fps,
                easing=transition_easing,  # type: ignore[arg-type]
            )

        scene_obj = Scene(
            version=1,
            view=view,
            size=Size(width=detected_width, height=detected_height),
            camera=camera,
            floor=floor,
            background=background,
            transition=transition,
            juicy=juicy,
            slides=slides,
        )

        scene_json = scene_obj.model_dump_json(by_alias=True, indent=2)
        out_path.write_text(scene_json, encoding="utf-8")
        print(str(out_path.resolve()))

    def _run(self, name: str, action, out: str) -> None:
        """Look up ENGINE and run ACTION, reporting NotImplemented/missing cleanly."""
        try:
            eng = get_engine(name)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            return
        try:
            action(eng)
            console.print(f"[green]Wrote[/green] {out} [dim](engine: {name})[/dim]")
        except NotImplementedError as exc:
            console.print(f"[yellow]Engine '{name}' not ready:[/yellow] {exc}")


def main() -> None:
    """Console-script entry point."""
    fire.Fire(Stax)


if __name__ == "__main__":
    main()
