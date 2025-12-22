# this_file: tests/test_config.py
"""Tests for shared configuration defaults and validation helpers."""

from __future__ import annotations

import pytest

import vexy_stax.config as config

pytestmark = pytest.mark.unit


def test_renderer_defaults_when_instantiated_then_matches_plan_values() -> None:
    defaults = config.DEFAULT_RENDERER

    assert defaults.width == 1920, "Width should default to 1080p baseline"
    assert defaults.height == 1080, "Height should default to 1080p baseline"
    assert defaults.scale == 1, "Scale should default to native 1× supersampling"
    assert defaults.padding == pytest.approx(1.1), (
        "Padding mirrors hero-shot front-fit plan (1.1×)"
    )


def test_animation_defaults_when_instantiated_then_matches_plan_values() -> None:
    defaults = config.DEFAULT_ANIMATION

    assert defaults.fps == 30, "Default fps should target smooth hero motion"
    assert defaults.duration == pytest.approx(2.0), (
        "Plan calls for a 2 second approach/retreat"
    )
    assert defaults.hold == pytest.approx(0.5), (
        "Front-view hold defaults to half a second"
    )
    assert defaults.easing == "power2.inOut", (
        "Easing identifier must mirror GSAP power2.inOut curve"
    )


def test_validate_scale_when_invalid_then_raises_value_error() -> None:
    with pytest.raises(ValueError) as exc:
        config.validate_scale(3)

    assert "Scale must be one of" in str(exc.value)


def test_validate_scale_when_valid_then_returns_scale() -> None:
    assert config.validate_scale(2) == 2


def test_validate_animation_timing_when_values_valid_then_no_error() -> None:
    config.validate_animation_timing(fps=30, duration=2.0, hold=0.5)


@pytest.mark.parametrize(
    ("fps", "duration", "hold", "expected_fragment"),
    [
        (5, 2.0, 0.5, "fps must be between"),
        (30, -1.0, 0.5, "duration must be greater"),
        (30, 2.0, -0.1, "hold must be between"),
    ],
)
def test_validate_animation_timing_when_invalid_then_raises_value_error(
    fps: int, duration: float, hold: float, expected_fragment: str
) -> None:
    with pytest.raises(ValueError) as exc:
        config.validate_animation_timing(fps=fps, duration=duration, hold=hold)

    assert expected_fragment in str(exc.value)
