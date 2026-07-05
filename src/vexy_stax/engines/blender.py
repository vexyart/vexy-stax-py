# this_file: src/vexy_stax/engines/blender.py
"""Blender engine — two-process photorealistic renderer (SPEC.md §5.3).

This (CLI-side) process computes all view geometry via ``vexy_stax.geometry``,
emits a FLAT render-job JSON, then spawns Blender headless to render it::

    blender --background --python _blender_render.py -- '{json}'

``_blender_render.py`` runs inside Blender's bundled Python and is a "dumb"
renderer: it only places plates/camera at the precomputed world coordinates and
sets per-plate alpha. All the math lives in ``geometry.py`` so every engine
agrees.

Render-job schema (what ``_build_*`` emits and ``_blender_render.py`` consumes)::

    {
      "width": int, "height": int,            # render resolution (pixels)
      "background": "#rrggbb",
      "floor": {"color": "#rrggbb", "reflectivity": float, "opacity": float},
      "edge": {"width": float, "color": "#rrggbb"},   # plate + caption-plate border (305/311)
      "floor_extent": float,                   # deck depth hint for floor sizing
      "turbo": bool,                           # Eevee + low samples when true
      "samples": int,
      "video": bool,                           # true ⇒ render the frame sequence
      "fps": int,                              # only used for video
      "output": "/abs/path.png|.mp4",
      "caption_anchor_x": float,              # world X for caption-plate LEFT edge (issue 332)
      "caption_plate_center_y": float,        # world Y for caption-plate vertical center
      "caption_plate_height": float,          # caption-plate height (== caption_size/0.75)
      "caption_pad_em": float,                # horizontal pad each side (× caption size)
      "slide_lift": float,                    # world Y lift of each slide plate (issue 332)
      "plates": [                              # one per slide, back-to-front
        {"path": "/abs.png", "reflection_path": "/abs.png"|null,
         "width": int, "height": int,
         # caption (issue 311): a white opaque bordered plate with centered text.
         "caption": {"text": str, "size": float, "color": str|None,
                     "font": str|None}|null}
      ],
      "frames": [                              # 1 entry for stills, N for video
        {
          "camera": {"position": [x,y,z], "target": [x,y,z],
                     "fov": float, "near": float},
          "gaps":   [float, ...],             # per-plate inter-plate gap (geometry.py)
          "opacities": [float, ...],          # per-plate effective alpha multiplier
          "caption_opacities": [float, ...]   # per-plate caption fade 0..1
        }
      ]
    }
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

from vexy_stax import geometry as geo
from vexy_stax.engines.base import register
from vexy_stax.images import read_images
from vexy_stax.scene import CaptionStyle, Scene, Slide, View

_RENDER_SCRIPT = str(Path(__file__).resolve().parent / "_blender_render.py")

# Blurred reflection textures are precomputed here (PIL is available CLI-side but
# NOT inside Blender's Python) and dropped in this temp dir; Blender loads them by
# path. The dir lives for the process so the spawned Blender can read the files.
_BLUR_DIR = Path(tempfile.mkdtemp(prefix="vexy_stax_blender_refl_"))


def _blurred_reflection_path(src_path: str, image_height_px: int) -> str:
    """Write a Gaussian-blurred copy of SRC for the floor reflection; return its path.

    The blur radius is ``geo.REFLECTION_BLUR_FRAC × image_height_px`` so the floor
    reflection reads as a soft, out-of-focus mirror (issue 303 §1) rather than a crisp
    copy. PIL only runs in this (CLI-side) process; the render script just loads the
    resulting PNG and flips it across the floor line. The alpha channel is blurred too so
    the soft silhouette feathers at the plate edges.
    """
    radius = max(0.5, geo.REFLECTION_BLUR_FRAC * float(image_height_px))
    # v2 (issue 325 speedup): the reflection is soft/out-of-focus, so blur a DOWNSCALED copy.
    # Blurring the full 6234×4030 source with a large radius cost ~4 s/image; a 1024px-tall copy
    # is visually identical under the glass and ~16× cheaper. The "v2" tag busts the old cache.
    out = _BLUR_DIR / f"refl_v2_{abs(hash((src_path, image_height_px))):016x}.png"
    if not out.exists():
        with Image.open(src_path) as src:
            im = src.convert("RGBA")
            cap = 1024
            if im.height > cap:
                s = cap / float(im.height)
                im = im.resize((max(1, round(im.width * s)), cap), Image.Resampling.BILINEAR)
                radius *= s
            blurred = im.filter(ImageFilter.GaussianBlur(radius=max(0.5, radius)))
        blurred.save(out, "PNG")
    return str(out)


def _find_blender() -> str:
    """Locate the Blender binary: PATH, then Homebrew, then the macOS app bundle."""
    found = shutil.which("blender")
    if found:
        return found
    for candidate in (
        "/opt/homebrew/bin/blender",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ):
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError("Blender not found. Install with: brew install --cask blender")


def _turbo(scene: Scene) -> bool:
    """Resolve turbo mode from a scene field (``juicy`` is unrelated) or env var.

    Turbo uses Eevee + low samples for fast previews and tests. Triggered by
    ``VEXY_STAX_TURBO=1`` (the canonical switch). Defaults to Cycles otherwise.
    """
    return os.environ.get("VEXY_STAX_TURBO", "") == "1"


def _caption_style(scene: Scene, slide: Slide) -> CaptionStyle | None:
    """Merge per-caption style over scene-level ``caption_defaults``."""
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


def _caption_font_path(font: str | None) -> str | None:
    """Resolve a caption font to a TTF *path* Blender can load (issue 328: default vexy-stax).

    A real font-file path is used as-is; anything else (an unset/default font, or a bare
    family name Blender's headless ``fonts.load`` can't resolve) falls back to the bundled
    ``vexy-stax.ttf`` (Zalando Sans Expanded) so the Python default font is the project default.
    """
    if font and os.path.isfile(font):
        return font
    default = geo.default_font_path()
    return str(default) if default else None


def _plate_jobs(scene: Scene) -> list[dict]:
    """Build the per-plate job entries (path/size/caption/reflection) from the scene."""
    infos = read_images([s.src for s in scene.slides])
    widest = max(info["width"] for info in infos) if infos else 1
    scale = scene.size.width / widest
    reflectivity = scene.floor.reflectivity

    jobs: list[dict] = []
    for slide, info in zip(scene.slides, infos, strict=True):
        caption = None
        # Issue 332: the global captions toggle suppresses ALL caption plates.
        if scene.captions and slide.caption is not None:
            style = _caption_style(scene, slide)
            # Default to the shared nominal caption size so 1em == size (matches the
            # em-based anchor/baseline) and stays consistent across engines.
            size = style.size if (style and style.size) else geo.caption_size(scene)
            caption = {
                "text": slide.caption.text,
                "size": size,
                "color": style.color if style else None,
                "font": _caption_font_path(style.font if style else None),
            }
        # Precompute the Gaussian-blurred reflection texture (PIL only runs here, not in
        # Blender). The render script flips it across the floor line; blurring (radius =
        # REFLECTION_BLUR_FRAC × image_h_px) makes the mirror soft (issue 303 §1).
        reflection_path = _blurred_reflection_path(info["path"], info["height"]) if reflectivity > 0 else None
        jobs.append(
            {
                "path": info["path"],
                "reflection_path": reflection_path,
                "width": info["width"] * scale,
                "height": info["height"] * scale,
                "caption": caption,
            }
        )
    return jobs


# ``vexy_stax.geometry`` and ``_blender_render.py`` share one frame (three.js
# Y-up: X = width, Y = up centered at 0, Z = depth with +Z toward the viewer,
# deck center at Z = -stack_depth/2). Geometry's poses are authoritative and
# already render-correct (compact head-on on +Z, expanded fit to the plate deck),
# so this engine just serializes them — no per-engine camera math.


def _camera_dict(pose: geo.CameraPose) -> dict:
    """Serialize a geometry ``CameraPose`` to the render-job camera schema."""
    return {
        "position": list(pose.position),
        "target": list(pose.target),
        "fov": pose.fov,
        "near": pose.near,
    }


def _still_frame(scene: Scene, view: View) -> dict:
    """Build the single frame-job for a still in ``view``.

    ``t`` is 1 for expanded, 0 for compact, matching ``interpolate_opacity``.
    Caption opacities come from ``geo.caption_opacities`` (the shared contract
    function) so all engines agree on the staggered fade behaviour.
    """
    if view == "expanded":
        camera = _camera_dict(geo.expanded_camera(scene))
        gaps = geo.plate_gaps(scene)
        t = 1.0
    else:
        camera = _camera_dict(geo.compact_camera(scene))
        gaps = [geo.MIN_GAP for _ in scene.slides]
        t = 0.0
    opacities = [s.resolved_opacity(view) for s in scene.slides]
    return {
        "camera": camera,
        "gaps": gaps,
        "opacities": opacities,
        "caption_opacities": geo.caption_opacities(scene, t),
    }


def _base_job(scene: Scene, out: Path, *, video: bool) -> dict:
    """Common render-job header shared by stills and video."""
    return {
        "width": scene.size.width,
        "height": scene.size.height,
        "background": scene.background,
        "floor": {
            "color": scene.floor.color,
            "reflectivity": scene.floor.reflectivity,
            "opacity": scene.floor.opacity,
        },
        # Plate edge border (issue 305): thickness in scene points (== plate-mesh units,
        # see note below) and color. The render script draws 4 thin quads per plate. When
        # width == 0 the border is skipped.
        "edge": {
            "width": geo.plate_edge_width(scene),
            "color": scene.edge.color,
        },
        # Floor shadows were removed (issue 312): plates cast NO shadow. The floor itself,
        # the blurry reflections and the plate edge borders remain.
        "floor_extent": geo.stack_depth(scene, "expanded"),
        "turbo": _turbo(scene),
        # Cycles: low samples + OpenImageDenoise + aggressive adaptive sampling = high quality
        # but fast for these flat plates (issue 320 §8 / 325 speedup — was 64, then 24).
        "samples": 8 if _turbo(scene) else 16,
        "video": video,
        "fps": scene.transition.fps if scene.transition else 30,
        "output": str(out.resolve()),
        "plates": _plate_jobs(scene),
        # Caption-plate layout (issue 311). Each caption is a small white opaque bordered
        # plate (fill #ffffff, border == plate edge in scene.edge.color/plate_edge_width)
        # with horizontally + vertically centered text. The plate's RIGHT edge sits at
        # caption_anchor_x and its vertical CENTER at caption_plate_center_y; its height is
        # caption_plate_height and its width is the measured text width + 2 × pad_em × size.
        # All values are in scene-coordinate units (same space as the scaled plate meshes),
        # so _blender_render.py (no vexy_stax import) consumes them directly (issue 302 §B).
        "caption_anchor_x": geo.caption_anchor_x(scene),
        "caption_plate_center_y": geo.caption_plate_center_y(scene),
        "caption_plate_height": geo.caption_plate_height(scene),
        "caption_pad_em": geo.CAPTION_PLATE_PAD_EM,
        # Issue 332: vertical lift (world Y) added to every slide plate so it sits ON TOP of its
        # on-floor caption plate (0 when captions are off → slides on the floor).
        "slide_lift": geo.slide_lift(scene),
        # Caption plate fill + border colors (issue 324): independently overridable, each
        # defaulting to scene.edge.color (so by default caption fill == caption border == slide border).
        "caption_fill_color": geo.caption_fill_color(scene),
        "caption_border_color": geo.caption_border_color(scene),
    }


def _build_image_job(scene: Scene, view: View, out: Path) -> dict:
    job = _base_job(scene, out, video=False)
    job["frames"] = [_still_frame(scene, view)]
    return job


def _build_video_job(scene: Scene, out: Path) -> dict:
    if scene.transition is None:
        raise ValueError("scene has no transition; nothing to animate (use render_image)")
    # Camera, gaps, opacities AND caption_opacities all come straight from
    # geometry's frame_plan — FrameState already carries caption_opacities.
    plan = geo.frame_plan(scene)

    job = _base_job(scene, out, video=True)
    # Issue 335 §3: video dimensions + fps come from scene.video (default to scene.size / 30),
    # overriding the still-render size in the shared base job and transition.fps.
    job["width"], job["height"] = geo.video_dimensions(scene)
    job["fps"] = geo.video_fps(scene)
    frames = []
    for state in plan:
        frames.append(
            {
                "camera": _camera_dict(state.camera),
                "gaps": list(state.gaps),
                "opacities": list(state.opacities),
                "caption_opacities": list(state.caption_opacities),
            }
        )
    job["frames"] = frames
    # Speed (issue 325): a Cycles transition is ~200 frames, and every compact-view frame crosses
    # the full transparent plate stack — at 4K that is ~1 h. The video is a MOTION preview (the
    # stills carry the full-res detail), so cap its long edge so it stays fast. Aspect is preserved
    # (3840×2480 → 1920×1240), so the framing is identical — only the pixel count drops ~4×.
    video_max_edge = 1920
    w, h = int(job["width"]), int(job["height"])
    if max(w, h) > video_max_edge:
        s = video_max_edge / float(max(w, h))
        job["width"] = max(1, round(w * s))
        job["height"] = max(1, round(h * s))
    return job


def _invoke(job: dict, out: Path) -> None:
    """Serialize JOB to JSON, run Blender headless, verify OUT exists & non-empty."""
    blender = _find_blender()
    cmd = [blender, "--background", "--python", _RENDER_SCRIPT, "--", json.dumps(job)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
        raise RuntimeError(f"Blender failed (exit {result.returncode}):\n{tail}")
    if not out.exists() or out.stat().st_size == 0:
        tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
        raise RuntimeError(f"Blender finished but {out} is missing/empty:\n{tail}")


class BlenderEngine:
    """Photorealistic Cycles/Eevee renderer (SPEC.md §5.3)."""

    name = "blender"

    def render_image(self, scene: Scene, view: View, out: Path) -> None:
        """Render a single still of SCENE in VIEW (compact|expanded)."""
        job = _build_image_job(scene, view, out)
        _invoke(job, out)

    def render_video(self, scene: Scene, out: Path) -> None:
        """Render SCENE's transition to an mp4 (requires ``scene.transition``)."""
        job = _build_video_job(scene, out)
        _invoke(job, out)


register(BlenderEngine())


if __name__ == "__main__":  # tiny manual harness: python -m ... not needed
    sys.exit("Import this module; do not run it directly.")
