# this_file: src/vexy_stax/engines/pygfx.py
"""pygfx engine — fast off-screen GPU renderer (SPEC.md §5.3).

This engine builds a pygfx scene that mirrors the shared coordinate convention
documented in ``vexy_stax.geometry`` (three.js Y-up: X = plate width centered at
0, Y = up with plates centered at Y = 0, Z = depth with the front plate at Z = 0
and +Z toward the viewer). All view math comes from ``geometry.py`` — this engine
only *draws* the precomputed camera pose, per-slide spacing and per-slide opacity,
so it agrees with the Blender and JS renderers.

Each slide is one textured ``plane_geometry`` sized to its pixel dimensions
(== points). A horizontal floor plane sits just below the tallest plate, and a
faded mirror copy of each plate below the floor line provides the floor
reflection (``floor.reflectivity``). Captions are ``gfx.Text`` objects placed
beneath each plate, fading per ``caption.show_in`` and the morph factor.

Rendering is fully off-screen via ``rendercanvas.offscreen`` (no window). Stills
are supersampled (``_SUPERSAMPLE``) and downscaled with Lanczos for clean edges.
Video renders ``geometry.frame_plan`` to a PNG sequence assembled with ffmpeg.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pygfx as gfx
import pylinalg as la
from PIL import Image
from rendercanvas.offscreen import RenderCanvas

from vexy_stax import geometry as geo
from vexy_stax.engines.base import register
from vexy_stax.scene import CaptionStyle, Scene, Slide, View

# Supersample factor for stills: render NxN larger then Lanczos-downscale. This
# is plain SSAA — it only improves edge quality, it does not change the scene.
_SUPERSAMPLE = 2
# Far plane is a large multiple of near so the deep expanded deck never clips.
_FAR_MULTIPLE = 100_000.0
# Caption sits this fraction of the plate height below the floor line.
_CAPTION_DROP = 0.10


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    """Parse a ``#rrggbb`` (or ``#rgb``) string into 0..1 RGB floats."""
    text = color.lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    r = int(text[0:2], 16) / 255.0
    g = int(text[2:4], 16) / 255.0
    b = int(text[4:6], 16) / 255.0
    return (r, g, b)


def _load_rgba(path: str) -> np.ndarray:
    """Load an image as a contiguous uint8 RGBA array for use as a texture."""
    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGBA"), dtype=np.uint8)
    return np.ascontiguousarray(arr)


def _caption_style(scene: Scene, slide: Slide) -> CaptionStyle | None:
    """Merge per-caption style over scene-level ``caption_defaults`` (best-effort)."""
    if slide.caption is None:
        return None
    base = scene.caption_defaults
    own = slide.caption.style
    if base is None and own is None:
        return None
    size = (own.size if own and own.size is not None else None) or (base.size if base else None)
    color = (own.color if own and own.color else None) or (base.color if base else None)
    font = (own.font if own and own.font else None) or (base.font if base else None)
    return CaptionStyle(size=size, color=color, font=font)


def _caption_opacity(slide: Slide, t_expanded: float) -> float:
    """Caption fade at morph factor ``t`` (0=compact, 1=expanded), honoring ``show_in``."""
    if slide.caption is None:
        return 0.0
    show = slide.caption.show_in
    if show == "both":
        return 1.0
    if show == "none":
        return 0.0
    t = max(0.0, min(1.0, t_expanded))
    return t if show == "expanded" else 1.0 - t


class _Deck:
    """Holds the pygfx scene graph and updates it per frame.

    Built once per render; ``set_frame`` mutates plate Z, plate/reflection alpha,
    caption alpha and the camera pose so a whole video reuses one GPU scene.
    """

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.world = gfx.Scene()
        self.world.add(gfx.Background(material=gfx.BackgroundMaterial(scene.background)))

        # Plate textures and pixel sizes (== points).
        self._sizes: list[tuple[int, int]] = []
        self._plates: list[gfx.Mesh] = []
        self._reflections: list[gfx.Mesh] = []
        self._captions: list[gfx.Text | None] = []

        tallest = 0
        arrays: list[np.ndarray] = []
        for slide in scene.slides:
            arr = _load_rgba(slide.src)
            arrays.append(arr)
            h, w = arr.shape[0], arr.shape[1]
            self._sizes.append((w, h))
            tallest = max(tallest, h)
        self._floor_y = -tallest / 2.0

        reflectivity = scene.floor.reflectivity
        for slide, arr, (w, h) in zip(scene.slides, arrays, self._sizes, strict=True):
            plate = gfx.Mesh(gfx.plane_geometry(w, h), self._make_image_material(arr))
            self.world.add(plate)
            self._plates.append(plate)

            if reflectivity > 0:
                refl = gfx.Mesh(gfx.plane_geometry(w, h), self._make_image_material(arr))
                # Mirror the plate across the floor line; render behind the floor.
                refl.local.scale = (1.0, -1.0, 1.0)
                refl.render_order = -1
                self.world.add(refl)
                self._reflections.append(refl)
            else:
                self._reflections.append(None)  # type: ignore[arg-type]

            self._captions.append(self._make_caption(scene, slide, w, h))

        self._add_floor(scene, tallest)

        self.camera = gfx.PerspectiveCamera(scene.camera.fov, scene.size.width / scene.size.height)

    @staticmethod
    def _make_image_material(arr: np.ndarray) -> gfx.MeshBasicMaterial:
        """A double-sided, alpha-blended textured material for a plate."""
        mat = gfx.MeshBasicMaterial(map=gfx.Texture(arr, dim=2))
        mat.alpha_mode = "blend"
        mat.side = "both"
        return mat

    def _add_floor(self, scene: Scene, tallest: int) -> None:
        """A horizontal floor plane just below the tallest plate."""
        depth = geo.stack_depth(scene, "expanded")
        widest = max(w for w, _ in self._sizes)
        extent_w = widest * 4.0
        extent_z = (depth + widest * 2.0) if depth > 0 else widest * 2.0
        mat = gfx.MeshBasicMaterial(color=_hex_to_rgb(scene.floor.color))
        mat.opacity = scene.floor.opacity
        mat.alpha_mode = "blend"
        floor = gfx.Mesh(gfx.plane_geometry(extent_w, extent_z), mat)
        floor.local.position = (0.0, self._floor_y, -depth / 2.0)
        floor.local.rotation = la.quat_from_axis_angle((1.0, 0.0, 0.0), -math.pi / 2.0)
        self.world.add(floor)

    def _make_caption(self, scene: Scene, slide: Slide, w: int, h: int) -> gfx.Text | None:
        """Build a caption text object beneath the plate (best-effort styling)."""
        if slide.caption is None:
            return None
        style = _caption_style(scene, slide)
        size = float(style.size) if style and style.size else max(12.0, h * 0.05)
        color = (style.color if style and style.color else None) or "#222222"
        text = gfx.Text(
            text=slide.caption.text,
            font_size=size,
            anchor="top-center",
            material=gfx.TextMaterial(color=color),
        )
        text.material.alpha_mode = "blend"
        # Below the floor line, centered under the plate; Z set per frame.
        text.local.position = (0.0, self._floor_y - h * _CAPTION_DROP, 0.0)
        self.world.add(text)
        return text

    def set_frame(self, state: geo.FrameState, t_expanded: float) -> None:
        """Place plates/captions and the camera for one frame state."""
        z_positions = geo._stack_positions(state.gaps)
        reflectivity = self.scene.floor.reflectivity
        for i, slide in enumerate(self.scene.slides):
            z = z_positions[i]
            alpha = state.opacities[i]
            plate = self._plates[i]
            plate.local.position = (0.0, 0.0, z)
            plate.material.opacity = alpha

            refl = self._reflections[i]
            if refl is not None:
                _, h = self._sizes[i]
                refl.local.position = (0.0, 2.0 * self._floor_y, z)
                refl.material.opacity = alpha * reflectivity

            cap = self._captions[i]
            if cap is not None:
                x, y, _ = cap.local.position
                cap.local.position = (x, y, z)
                cap.material.opacity = _caption_opacity(slide, t_expanded)

        pose = state.camera
        self.camera.fov = pose.fov
        self.camera.local.position = pose.position
        self.camera.show_pos(pose.target)
        self.camera.depth_range = (pose.near, max(pose.near * _FAR_MULTIPLE, _FAR_MULTIPLE))


def _render_frame(deck: _Deck, width: int, height: int, supersample: int) -> Image.Image:
    """Render the current deck state to a downscaled RGBA Pillow image."""
    canvas = RenderCanvas(size=(width, height), pixel_ratio=supersample)
    renderer = gfx.WgpuRenderer(canvas)
    renderer.render(deck.world, deck.camera)
    raw = np.asarray(canvas.draw())
    im = Image.fromarray(raw, mode="RGBA")
    if supersample != 1:
        im = im.resize((width, height), Image.LANCZOS)
    return im


def _still_state(scene: Scene, view: View) -> tuple[geo.FrameState, float]:
    """The single FrameState (and morph factor) for a still in ``view``."""
    if view == "expanded":
        camera = geo.expanded_camera(scene)
        gaps = geo.plate_gaps(scene)
        t = 1.0
    else:
        camera = geo.compact_camera(scene)
        gaps = [geo.MIN_GAP for _ in scene.slides]
        t = 0.0
    opacities = [s.resolved_opacity(view) for s in scene.slides]
    return geo.FrameState(camera=camera, gaps=gaps, opacities=opacities), t


class PygfxEngine:
    """Fast GPU off-screen renderer (SPEC.md §5.3)."""

    name = "pygfx"

    def render_image(self, scene: Scene, view: View, out: Path) -> None:
        """Render a single still of SCENE in VIEW (compact|expanded) to a PNG."""
        deck = _Deck(scene)
        state, t = _still_state(scene, view)
        deck.set_frame(state, t)
        im = _render_frame(deck, scene.size.width, scene.size.height, _SUPERSAMPLE)
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "PNG")

    def render_video(self, scene: Scene, out: Path) -> None:
        """Render SCENE's transition to an mp4 (requires ``scene.transition``)."""
        if scene.transition is None:
            raise ValueError("scene has no transition; nothing to animate (use render_image)")
        _require_ffmpeg()
        plan = geo.frame_plan(scene)
        factors = _morph_factors(scene)
        if not plan:
            raise ValueError("transition produced no frames")

        deck = _Deck(scene)
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="vexy_stax_pygfx_") as tmp:
            tmp_dir = Path(tmp)
            for i, (state, t) in enumerate(zip(plan, factors, strict=True)):
                deck.set_frame(state, t)
                # No supersample for video frames: many frames, speed matters.
                im = _render_frame(deck, scene.size.width, scene.size.height, 1)
                im.convert("RGB").save(tmp_dir / f"frame_{i:05d}.png", "PNG")
            _encode_video(tmp_dir, scene.transition.fps, out)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg finished but {out} is missing/empty")


def _morph_factors(scene: Scene) -> list[float]:
    """Per-frame morph factor (0=compact, 1=expanded), matching ``frame_plan``.

    Mirrors ``geometry.frame_plan``'s leg/hold layout so caption fades stay in
    lockstep with the camera/opacity morph it produced.
    """
    tr = scene.transition
    assert tr is not None
    leg_frames = round(tr.duration * tr.fps)
    wait_frames = round(tr.wait * tr.fps)
    legs = geo._LEGS[tr.kind]
    factors: list[float] = []
    for start, end in legs:
        for i in range(leg_frames):
            p = i / leg_frames if leg_frames else 0.0
            eased = geo.ease(tr.easing, p)
            factors.append(start + (end - start) * eased)
        factors.extend(end for _ in range(wait_frames))
    return factors


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise an actionable error."""
    found = shutil.which("ffmpeg")
    if not found:
        raise FileNotFoundError("ffmpeg not found on PATH. Install with: brew install ffmpeg")
    return found


def _encode_video(frame_dir: Path, fps: int, out: Path) -> None:
    """Assemble a PNG sequence into an H.264 mp4 with ffmpeg."""
    ffmpeg = _require_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frame_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{tail}")


register(PygfxEngine())
