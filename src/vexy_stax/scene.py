# this_file: src/vexy_stax/scene.py
"""Pydantic v2 models for the vexy-stax shared scene format v1.

Mirrors ``schema/vexy-stax-scene.schema.json`` exactly. Parse, don't validate:
every model sets ``extra="forbid"`` so unknown fields fail loud at the boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

View = Literal["expanded", "compact"]
TransitionKind = Literal["expand", "collapse", "expand_collapse", "collapse_expand"]
ShowIn = Literal["expanded", "compact", "both", "none"]
Easing = Literal["linear", "easeInOutCubic", "easeOutCubic", "easeInCubic"]

# distance: absolute points as number/string, or a "P%" viewport-fit percentage.
DISTANCE_PATTERN = r"^[0-9]+(\.[0-9]+)?%?$"
Distance = float | str


class Size(BaseModel):
    """Render dimensions in pixels (= points)."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=1920, ge=1)
    height: int = Field(default=1080, ge=1)


class Camera(BaseModel):
    """Camera and expanded-spacing settings."""

    model_config = ConfigDict(extra="forbid")

    gap: float = Field(default=1920, ge=0, description="Points between adjacent plates (expanded).")
    distance: Distance = Field(default="100%", description='Absolute points or viewport-fit "P%".')
    angle: float = Field(default=60, description="Azimuth degrees for expanded view.")
    elevation: float = Field(default=0, description="Degrees above horizon for expanded view.")
    fov: float = Field(default=39.6, gt=0, lt=180)


class Transition(BaseModel):
    """Animated morph between the two views."""

    model_config = ConfigDict(extra="forbid")

    kind: TransitionKind
    duration: float = Field(default=3.0, gt=0, description="Seconds per leg.")
    wait: float = Field(default=1.0, ge=0, description="Hold seconds at the far end.")
    fps: int = Field(default=30, ge=1)
    easing: Easing = "easeInOutCubic"


class Video(BaseModel):
    """Video render parameters centralized in the scene (issue 335 §3).

    Engines read these for video rendering, overriding the legacy ``transition``-derived
    values. ``transition`` still owns the ANIMATION definition (``kind``/``easing``/``wait``/
    ``duration``); ``video`` owns the OUTPUT framing (dimensions/fps/frame counts/held stills).

    Precedence (documented, issue 335 §3):

    * ``width``/``height`` default to ``scene.size`` when ``None``.
    * ``fps`` (default ``None``) overrides ``transition.fps`` for video rendering when set;
      when ``None`` it falls back to ``transition.fps`` (else 30), preserving prior behavior.
    * ``frames`` is the number of TRANSITION frames PER LEG. ``None`` (default) preserves the
      legacy behavior: ``round(transition.duration * fps)`` frames per leg.
    * ``first_hold``/``last_hold`` (default 10 each) prepend/append that many copies of the
      first/last :class:`~vexy_stax.geometry.FrameState` so the clip holds the opening and
      closing stills (still → transition → still). Set to 0 to disable.

    Any of these can be overridden at the call site (function args / CLI flags) without
    editing the scene file.
    """

    model_config = ConfigDict(extra="forbid")

    width: int | None = Field(default=None, ge=1, description="Video width; null ⇒ scene.size.width.")
    height: int | None = Field(default=None, ge=1, description="Video height; null ⇒ scene.size.height.")
    fps: int | None = Field(
        default=None, ge=1, description="Video fps; null ⇒ transition.fps (else 30). Overrides when set."
    )
    frames: int | None = Field(
        default=None, ge=1, description="Transition frames PER LEG; null ⇒ round(transition.duration * fps)."
    )
    first_hold: int = Field(default=10, ge=0, description="Held copies of the FIRST frame (still intro).")
    last_hold: int = Field(default=10, ge=0, description="Held copies of the LAST frame (still outro).")


class Floor(BaseModel):
    """Floor plane appearance — a (by default invisible) pane that blurrily reflects the plates.

    Default (issue 342 follow-up): no visible floor PANE (white, ``opacity`` 0.0) but a faint
    blurred reflection of the plates (``reflectivity`` 0.1) — clean on a white page, no grey
    smoked-glass "shadow". Raise ``opacity`` (and/or darken ``color``) for a visible floor.
    ``reflectivity`` scales the reflection strength.
    """

    model_config = ConfigDict(extra="forbid")

    color: str = "#ffffff"  # floor pane tint (invisible by default since opacity is 0)
    opacity: float = Field(default=0.0, ge=0, le=1)  # 0 = no visible floor pane (just reflections)
    reflectivity: float = Field(default=0.1, ge=0, le=1)  # faint blurred plate reflections


class Edge(BaseModel):
    """Optional plate border (issue 305) — a thin frame around each plate's rectangle.

    Off by default (issue 326: ``width == 0`` ⇒ no slide-plate border and no caption-plate
    border). Set ``width > 0`` to draw a frame in ``color`` around both.
    """

    model_config = ConfigDict(extra="forbid")

    width: float = Field(default=0.0, ge=0, description="Border thickness, fraction of plate height (0 = off).")
    color: str = "#f2f2f2"  # slide-plate + caption border color when enabled (issue 324 default)


class CaptionStyle(BaseModel):
    """Engine-best-effort caption styling (text + plate fill/border colors).

    ``color`` is the caption TEXT color; ``fill_color``/``border_color`` are the caption
    PLATE background + border colors (issue 324, each overridable). When fill/border are
    unset, engines fall back to ``scene.edge.color`` (so by default the caption plate fill,
    caption border and slide border all match).
    """

    model_config = ConfigDict(extra="forbid")

    size: float | None = Field(default=None, gt=0)
    color: str | None = None  # caption TEXT color
    font: str | None = None
    fill_color: str | None = None  # caption plate fill (issue 324; default scene.edge.color)
    border_color: str | None = None  # caption plate border (issue 324; default scene.edge.color)


class CaptionFade(BaseModel):
    """Customizable caption fade-in timing during a transition (issue 302 §B.4)."""

    model_config = ConfigDict(extra="forbid")

    window: float = Field(
        default=0.9, gt=0, le=1, description="Fraction of the morph (from the end) over which captions fade in."
    )
    stagger: float = Field(
        default=0.3, ge=0, lt=1, description="Back→front succession spread, as a fraction of the fade window."
    )
    stagger_frames: int | None = Field(
        default=None,
        ge=0,
        description="Issue 309: back→front per-caption step in transition FRAMES; overrides `stagger` when set.",
    )


class OpacityPerView(BaseModel):
    """Per-view opacity, interpolated during transitions."""

    model_config = ConfigDict(extra="forbid")

    expanded: float = Field(default=1.0, ge=0, le=1)
    compact: float = Field(default=1.0, ge=0, le=1)


Opacity = float | OpacityPerView


class Caption(BaseModel):
    """Text label beneath a plate."""

    model_config = ConfigDict(extra="forbid")

    text: str
    show_in: ShowIn = "expanded"
    style: CaptionStyle | None = None


class Slide(BaseModel):
    """A single layered image plate."""

    model_config = ConfigDict(extra="forbid")

    src: str = Field(description="Path relative to the scene file, or a data: URI.")
    gap: float | None = Field(default=None, ge=0, description="Per-slide gap override; null uses camera.gap.")
    opacity: Opacity = 1.0
    caption: Caption | None = None

    def resolved_opacity(self, view: View) -> float:
        """Return the opacity for ``view`` (scalar opacity returns itself)."""
        if isinstance(self.opacity, OpacityPerView):
            return self.opacity.expanded if view == "expanded" else self.opacity.compact
        return float(self.opacity)


class Scene(BaseModel):
    """Top-level scene document."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    view: View = "expanded"
    size: Size = Field(default_factory=Size)
    camera: Camera = Field(default_factory=Camera)
    transition: Transition | None = None
    # Issue 335 §3: video render params (dimensions/fps/frame counts/held stills). Always present
    # with defaults so engines can read scene.video without a None check; defaults preserve the
    # prior showcase behavior (held frames default to 10/10).
    video: Video = Field(default_factory=Video)
    floor: Floor = Field(default_factory=Floor)
    edge: Edge = Field(default_factory=Edge)  # issue 305: visible plate border (default-on)
    background: str = "#ffffff"
    juicy: bool = False
    # Issue 332: global captions on/off toggle. When ON (default — preserves prior behavior),
    # each slide plate sits ON TOP of its on-floor caption plate (the stacked layout). When
    # OFF, no caption plates are drawn and the slide plates sit directly on the floor.
    captions: bool = True
    caption_defaults: CaptionStyle | None = None
    caption_fade: CaptionFade | None = None
    slides: list[Slide] = Field(min_length=1, description="Ordered back-to-front; index 0 is farthest.")
    # Schema permits a "$schema" pointer key; accept and ignore it.
    schema_ref: str | None = Field(default=None, alias="$schema")


def _resolve_src(src: str, base_dir: Path) -> str:
    """Resolve a slide ``src`` relative to ``base_dir`` into an absolute path.

    ``data:`` URIs are left untouched (no filesystem resolution).
    """
    if src.startswith("data:"):
        return src
    p = Path(src)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return str(p)


def load_scene(path: str | Path) -> Scene:
    """Read, validate, and path-resolve a scene JSON file.

    Each slide ``src`` is resolved relative to the scene file's directory into an
    absolute path (``data:`` URIs are preserved). Validation errors are pydantic's
    own, which point at the offending field.
    """
    scene_path = Path(path).resolve()
    raw = json.loads(scene_path.read_text(encoding="utf-8"))
    scene = Scene.model_validate(raw)
    base_dir = scene_path.parent
    for slide in scene.slides:
        slide.src = _resolve_src(slide.src, base_dir)
    return scene
