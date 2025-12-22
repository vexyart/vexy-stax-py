# this_file: vexy-stax-py/src/vexy_stax/config.py
"""Shared configuration defaults and validation helpers for the pygfx renderer.

The values mirror the plan outlined in issues/101.md:
- animation defaults target a 2s hero move with a 0.5s front-view hold at 30 fps
  using the GSAP-like ``power2.inOut`` easing curve
- still exports render at 1920x1080 by default with supersampling scales of 1×/2×/4×
- camera fitting applies an 1.1 padding multiplier to avoid clipping during the hero pose
"""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_SCALES: tuple[int, int, int] = (1, 2, 4)
MIN_FPS = 12
MAX_FPS = 120
MIN_DURATION = 0.2  # seconds
MAX_DURATION = 60.0
MIN_HOLD = 0.0
MAX_HOLD = 20.0
DEFAULT_PADDING = 1.1

# Minimum gap between slides to prevent z-fighting when Layer Depth is 0.
# Matches JS MIN_LAYER_GAP constant.
MIN_LAYER_GAP = 3.0

# Floor position (Y=0, slides sit on top)
FLOOR_Y = 0.0


@dataclass(slots=True, frozen=True)
class RendererDefaults:
    """Default resolution and sampling parameters."""

    width: int = 1920
    height: int = 1080
    scale: int = 1
    padding: float = DEFAULT_PADDING


@dataclass(slots=True, frozen=True)
class AnimationDefaults:
    """Default hero shot timing parameters."""

    fps: int = 30
    duration: float = 2.0
    hold: float = 0.5
    easing: str = "power2.inOut"


DEFAULT_RENDERER = RendererDefaults()
DEFAULT_ANIMATION = AnimationDefaults()


def validate_scale(scale: int) -> int:
    """Ensure the requested render scale is supported (1×, 2×, or 4×)."""

    if scale not in ALLOWED_SCALES:
        allowed = ", ".join(str(value) for value in ALLOWED_SCALES)
        msg = f"Scale must be one of {allowed}; received {scale}"
        raise ValueError(msg)
    return scale


def validate_animation_timing(*, fps: int, duration: float, hold: float) -> None:
    """Validate hero shot timing values before running the animation timeline."""

    if fps < MIN_FPS or fps > MAX_FPS:
        msg = f"fps must be between {MIN_FPS} and {MAX_FPS}; received {fps}"
        raise ValueError(msg)

    if duration <= 0 or duration > MAX_DURATION:
        msg = (
            f"duration must be greater than 0 and at most {MAX_DURATION} seconds; "
            f"received {duration}"
        )
        raise ValueError(msg)

    if hold < MIN_HOLD or hold > MAX_HOLD:
        msg = f"hold must be between {MIN_HOLD} and {MAX_HOLD} seconds; received {hold}"
        raise ValueError(msg)


__all__ = [
    "ALLOWED_SCALES",
    "DEFAULT_ANIMATION",
    "DEFAULT_PADDING",
    "DEFAULT_RENDERER",
    "FLOOR_Y",
    "MIN_LAYER_GAP",
    "AnimationDefaults",
    "RendererDefaults",
    "validate_animation_timing",
    "validate_scale",
]
