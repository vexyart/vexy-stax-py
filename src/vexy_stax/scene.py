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
    distance: Distance = Field(default="90%", description='Absolute points or viewport-fit "P%".')
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


class Floor(BaseModel):
    """Floor plane appearance."""

    model_config = ConfigDict(extra="forbid")

    color: str = "#f2f2f2"
    opacity: float = Field(default=1.0, ge=0, le=1)
    reflectivity: float = Field(default=0.5, ge=0, le=1)


class CaptionStyle(BaseModel):
    """Engine-best-effort caption styling."""

    model_config = ConfigDict(extra="forbid")

    size: float | None = Field(default=None, gt=0)
    color: str | None = None
    font: str | None = None


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
    floor: Floor = Field(default_factory=Floor)
    background: str = "#ffffff"
    juicy: bool = False
    caption_defaults: CaptionStyle | None = None
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
