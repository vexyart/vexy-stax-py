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
      "floor_extent": float,                   # deck depth hint for floor sizing
      "turbo": bool,                           # Eevee + low samples when true
      "samples": int,
      "video": bool,                           # true ⇒ render the frame sequence
      "fps": int,                              # only used for video
      "output": "/abs/path.png|.mp4",
      "plates": [                              # one per slide, back-to-front
        {"path": "/abs.png", "width": int, "height": int,
         "caption": {"text": str, "size": float|None, "color": str|None}|null}
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
from pathlib import Path

from vexy_stax import geometry as geo
from vexy_stax.engines.base import register
from vexy_stax.images import read_images
from vexy_stax.scene import CaptionStyle, Scene, Slide, View

_RENDER_SCRIPT = str(Path(__file__).resolve().parent / "_blender_render.py")


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


def _plate_jobs(scene: Scene) -> list[dict]:
    """Build the per-plate job entries (path/size/caption) from the scene."""
    infos = read_images([s.src for s in scene.slides])
    jobs: list[dict] = []
    for slide, info in zip(scene.slides, infos, strict=True):
        caption = None
        if slide.caption is not None:
            style = _caption_style(scene, slide)
            caption = {
                "text": slide.caption.text,
                "size": style.size if style else None,
                "color": style.color if style else None,
            }
        jobs.append(
            {
                "path": info["path"],
                "width": info["width"],
                "height": info["height"],
                "caption": caption,
            }
        )
    return jobs


def _caption_opacity(slide: Slide, t_expanded: float) -> float:
    """Caption fade at morph factor ``t`` (0=compact, 1=expanded).

    Honors ``show_in``: an "expanded" caption is 0 in compact and lerps to 1 as
    the deck expands; "compact" is the inverse; "both" is always on; "none" off.
    """
    if slide.caption is None:
        return 0.0
    show = slide.caption.show_in
    if show == "both":
        return 1.0
    if show == "none":
        return 0.0
    if show == "expanded":
        return max(0.0, min(1.0, t_expanded))
    return max(0.0, min(1.0, 1.0 - t_expanded))  # compact


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
        "caption_opacities": [_caption_opacity(s, t) for s in scene.slides],
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
        "floor_extent": geo.stack_depth(scene, "expanded"),
        "turbo": _turbo(scene),
        "samples": 16 if _turbo(scene) else 128,
        "video": video,
        "fps": scene.transition.fps if scene.transition else 30,
        "output": str(out.resolve()),
        "plates": _plate_jobs(scene),
    }


def _build_image_job(scene: Scene, view: View, out: Path) -> dict:
    job = _base_job(scene, out, video=False)
    job["frames"] = [_still_frame(scene, view)]
    return job


def _build_video_job(scene: Scene, out: Path) -> dict:
    if scene.transition is None:
        raise ValueError("scene has no transition; nothing to animate (use render_image)")
    # Camera, gaps and opacities all come straight from geometry's frame plan
    # (now render-correct). Caption fades use the matching per-frame morph factor.
    plan = geo.frame_plan(scene)
    factors = _morph_factors(scene)

    job = _base_job(scene, out, video=True)
    frames = []
    for state, t in zip(plan, factors, strict=True):
        frames.append(
            {
                "camera": _camera_dict(state.camera),
                "gaps": list(state.gaps),
                "opacities": list(state.opacities),
                "caption_opacities": [_caption_opacity(s, t) for s in scene.slides],
            }
        )
    job["frames"] = frames
    return job


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
