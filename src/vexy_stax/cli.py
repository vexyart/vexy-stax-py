# this_file: src/vexy_stax/cli.py
"""fire + rich CLI for vexy-stax (SPEC.md §5.2)."""

from __future__ import annotations

from pathlib import Path

import fire
from rich.console import Console

from vexy_stax.engines import available_engines, get_engine
from vexy_stax.images import overlay_images, read_images
from vexy_stax.scene import View, load_scene

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

    def video(self, scene: str, engine: str | None = None, out: str = "out.mp4") -> None:
        """Render SCENE's transition to a video file."""
        sc = load_scene(scene)
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
