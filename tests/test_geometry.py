# this_file: tests/test_geometry.py
"""Tests for engine-agnostic geometry math (SPEC.md §3).

Fixture vectors are kept explicit so the JS ``geometry.js`` can later match them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vexy_stax import geometry as g
from vexy_stax.scene import Scene, load_scene

EXAMPLE = Path(__file__).resolve().parents[1] / "testdata" / "airbl.scene.json"

EASINGS = ["linear", "easeInOutCubic", "easeOutCubic", "easeInCubic"]


@pytest.fixture
def scene() -> Scene:
    return load_scene(EXAMPLE)


@pytest.mark.parametrize("name", EASINGS)
def test_ease_endpoints(name: str) -> None:
    assert g.ease(name, 0.0) == pytest.approx(0.0)
    assert g.ease(name, 1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("name", EASINGS)
def test_ease_clamps(name: str) -> None:
    assert g.ease(name, -5.0) == pytest.approx(0.0)
    assert g.ease(name, 5.0) == pytest.approx(1.0)


def test_ease_midpoint_values() -> None:
    assert g.ease("linear", 0.5) == pytest.approx(0.5)
    assert g.ease("easeInOutCubic", 0.5) == pytest.approx(0.5)
    assert g.ease("easeInCubic", 0.5) == pytest.approx(0.125)
    assert g.ease("easeOutCubic", 0.5) == pytest.approx(0.875)


def test_ease_unknown_raises() -> None:
    with pytest.raises(ValueError):
        g.ease("bogus", 0.5)


def test_interpolate_opacity_lerps(scene: Scene) -> None:
    halftone = scene.slides[7]  # expanded=1.0, compact=0.4
    assert g.interpolate_opacity(halftone, 0.0) == pytest.approx(0.4)
    assert g.interpolate_opacity(halftone, 1.0) == pytest.approx(1.0)
    assert g.interpolate_opacity(halftone, 0.5) == pytest.approx(0.7)


def test_interpolate_opacity_scalar(scene: Scene) -> None:
    source = scene.slides[0]  # scalar 1.0
    assert g.interpolate_opacity(source, 0.0) == pytest.approx(1.0)
    assert g.interpolate_opacity(source, 0.5) == pytest.approx(1.0)


def test_stack_depth_expanded_vs_compact(scene: Scene) -> None:
    n = len(scene.slides)  # 8
    compact = g.stack_depth(scene, "compact")
    expanded = g.stack_depth(scene, "expanded")
    assert compact == pytest.approx((n - 1) * g.MIN_GAP)  # 7 * 3 = 21
    assert expanded == pytest.approx((n - 1) * scene.camera.gap)  # 7 * 480 = 3360
    assert expanded > compact


def test_camera_near_scales_with_distance(scene: Scene) -> None:
    cam = g.expanded_camera(scene)
    # distance is |position - target|
    dist = sum((p - t) ** 2 for p, t in zip(cam.position, cam.target)) ** 0.5
    assert cam.near == pytest.approx(max(1.0, dist * 0.005))
    assert cam.near > 1.0  # large deck -> near above the floor of 1.0


def test_compact_camera_head_on_plus_z(scene: Scene) -> None:
    cam = g.compact_camera(scene)
    # head-on: camera sits on +Z in front of the target (toward the viewer)
    assert cam.position[2] > cam.target[2]
    assert cam.position[0] == pytest.approx(cam.target[0])
    assert cam.position[1] == pytest.approx(cam.target[1])
    # Dual-axis crop-free fit (issue 302 §1, 303 §2): distance = max(d_w, d_h) + depth/2.
    import math

    frac = float(str(scene.camera.distance).rstrip("%")) / 100.0  # "100%" -> 1.0 (fit tight)
    hfov = math.radians(scene.camera.fov)
    aspect = scene.size.width / scene.size.height
    vfov = 2.0 * math.atan(math.tan(hfov / 2.0) / aspect)
    d_w = scene.size.width / (2.0 * math.tan(hfov / 2.0) * frac)
    d_h = scene.size.height / (2.0 * math.tan(vfov / 2.0) * frac)
    expected_distance = max(d_w, d_h) + g.stack_depth(scene, "compact") / 2.0
    assert cam.position[2] - cam.target[2] == pytest.approx(expected_distance)


def test_compact_camera_no_crop_limiting_axis_at_pct(scene: Scene) -> None:
    """Front plate fits with no crop; the limiting axis touches exactly P% (303: P=100, fit tight)."""
    import math

    frac = float(str(scene.camera.distance).rstrip("%")) / 100.0
    cam = g.compact_camera(scene)
    d = cam.position[2] - 0.0  # camera->front plate (Z=0) along view axis
    hfov = math.radians(scene.camera.fov)
    aspect = scene.size.width / scene.size.height
    vfov = 2.0 * math.atan(math.tan(hfov / 2.0) / aspect)
    fill_w = (scene.size.width / 2.0) / (d * math.tan(hfov / 2.0))
    fill_h = (scene.size.height / 2.0) / (d * math.tan(vfov / 2.0))
    assert fill_w <= 1.0 + 1e-9 and fill_h <= 1.0 + 1e-9  # no crop on either axis
    assert max(fill_w, fill_h) == pytest.approx(frac)  # limiting axis touches exactly P%


def _project_expanded_ndc(scene: Scene, cam: g.CameraPose):
    """Project the deck at ``cam`` → (left margin, right margin, mean center gap, max|ndc_y|)."""
    import math

    hfov = math.radians(scene.camera.fov)
    aspect = scene.size.width / scene.size.height
    th = math.tan(hfov / 2.0)
    tv = math.tan(2.0 * math.atan(th / aspect) / 2.0)
    look = g._normalize(g._sub(cam.target, cam.position))
    right = g._normalize(g._cross(look, (0.0, 1.0, 0.0)))
    up = g._normalize(g._cross(right, look))
    hw, hh = scene.size.width / 2.0, scene.size.height / 2.0
    a, b, ymax = math.inf, -math.inf, 0.0
    centers = []
    for z in g._stack_positions(g.plate_gaps(scene)):
        relc = g._sub((0.0, 0.0, z), cam.position)
        centers.append(g._dot(relc, right) / (g._dot(relc, look) * th))
        for sx in (-hw, hw):
            for sy in (-hh, hh):
                rel = g._sub((sx, sy, z), cam.position)
                zv = g._dot(rel, look)
                nx = g._dot(rel, right) / (zv * th)
                a, b = min(a, nx), max(b, nx)
                ymax = max(ymax, abs(g._dot(rel, up) / (zv * tv)))
    cgaps = [abs(centers[i + 1] - centers[i]) for i in range(len(centers) - 1)]
    gap = sum(cgaps) / len(cgaps)
    return a + 1.0, 1.0 - b, gap, ymax


def test_expanded_camera_margins_match_gap(scene: Scene) -> None:
    """Issue 302 §2: left margin == right margin == projected inter-plate gap, no crop."""
    cam = g.expanded_camera(scene)
    assert cam.position[1] == pytest.approx(0.0)  # elevation 0 keeps camera at deck height
    assert cam.position[2] > cam.target[2]  # toward the viewer (+Z)
    margin_l, margin_r, gap, ymax = _project_expanded_ndc(scene, cam)
    assert margin_l == pytest.approx(margin_r, abs=1e-3)  # equal L/R margins
    assert margin_l == pytest.approx(gap, abs=1e-3)  # margin == projected gap
    assert margin_l > 0.0 and ymax <= g.V_FILL + 1e-6  # all plates inside the frame


def test_plate_gaps_fallback(scene: Scene) -> None:
    gaps = g.plate_gaps(scene)
    assert len(gaps) == len(scene.slides)
    assert all(x == pytest.approx(scene.camera.gap) for x in gaps)


def test_frame_plan_length(scene: Scene) -> None:
    # expand_collapse: 2 legs; duration 4.0 * 20 = 80 frames/leg; wait 1.0 * 20 = 20
    plan = g.frame_plan(scene)
    expected = 2 * (round(4.0 * 20) + round(1.0 * 20))  # 2 * (80 + 20) = 200
    assert len(plan) == expected == 200


def test_frame_plan_empty_without_transition(scene: Scene) -> None:
    scene.transition = None
    assert g.frame_plan(scene) == []


def test_frame_plan_endpoints_opacity(scene: Scene) -> None:
    plan = g.frame_plan(scene)
    halftone_idx = 7
    # expand_collapse starts compact (t=0): halftone opacity 0.4
    assert plan[0].opacities[halftone_idx] == pytest.approx(0.4)
    # at the end of leg 1 (frame 80 = first hold frame), fully expanded: 1.0
    assert plan[80].opacities[halftone_idx] == pytest.approx(1.0)


def test_caption_opacities_invisible_in_compact(scene: Scene) -> None:
    # every caption is show_in="expanded" -> fully invisible at t=0 (compact)
    assert g.caption_opacities(scene, 0.0) == pytest.approx([0.0] * len(scene.slides))


def test_caption_opacities_full_in_expanded(scene: Scene) -> None:
    # full opacity ONLY in the expanded view: all expanded captions reach 1.0 at t=1
    assert g.caption_opacities(scene, 1.0) == pytest.approx([1.0] * len(scene.slides))


def test_caption_opacities_stagger_back_to_front(scene: Scene) -> None:
    # mid-fade: backmost (index 0) leads, frontmost trails (strictly decreasing)
    ops = g.caption_opacities(scene, 0.5)
    assert all(ops[i] > ops[i + 1] for i in range(len(ops) - 1))
    assert ops[0] > 0.0  # backmost already fading in


def test_caption_opacities_window_and_show_in() -> None:
    # window=1.0, stagger=0 -> a single expanded caption fades linearly over all of t.
    from vexy_stax.scene import Caption, CaptionFade, Scene, Size, Slide

    sc = Scene(
        size=Size(width=100, height=100),
        caption_fade=CaptionFade(window=1.0, stagger=0.0),
        slides=[
            Slide(src="a", caption=Caption(text="x", show_in="expanded")),
            Slide(src="b", caption=Caption(text="y", show_in="both")),
            Slide(src="c", caption=Caption(text="z", show_in="none")),
            Slide(src="d"),  # no caption
        ],
    )
    assert g.caption_opacities(sc, 0.0) == pytest.approx([0.0, 1.0, 0.0, 0.0])
    assert g.caption_opacities(sc, 0.5) == pytest.approx([0.5, 1.0, 0.0, 0.0])
    assert g.caption_opacities(sc, 1.0) == pytest.approx([1.0, 1.0, 0.0, 0.0])


def test_frame_state_carries_caption_opacities(scene: Scene) -> None:
    plan = g.frame_plan(scene)
    assert plan[0].caption_opacities == pytest.approx([0.0] * len(scene.slides))  # compact start
    assert plan[80].caption_opacities == pytest.approx([1.0] * len(scene.slides))  # expanded hold


def test_caption_layout_em_based(scene: Scene) -> None:
    """Issues 321/323: caption plate right edge touches slide plate left edge (0em gap); baseline 1em above ground."""
    s = g.caption_size(scene)
    # issue 316: the testdata carries explicit caption font + size entries (size == the 315
    # default of 7.5% of plate height); caption_size resolves caption_defaults.size when set.
    assert scene.caption_defaults.size is not None
    assert scene.caption_defaults.font is None  # issue 328: testdata uses the bundled default font
    assert s == pytest.approx(float(scene.caption_defaults.size))
    # issue 324: the *default* (no explicit size) is now 10% of the plate height (1/3 larger
    # than the 315 default of 7.5%); testdata size tracks that.
    assert g.CAPTION_DEFAULT_SIZE_FRAC == pytest.approx(0.10)
    assert scene.caption_defaults.size == pytest.approx(scene.size.height * g.CAPTION_DEFAULT_SIZE_FRAC, abs=1.0)
    # issues 321/323: CAPTION_GAP_EM=0 so right edge of caption plate touches left edge of slide plate
    assert g.caption_anchor_x(scene) == pytest.approx(-(scene.size.width / 2.0 + g.CAPTION_GAP_EM * s))
    # baseline 1em (size) above the ground (floor at -height/2)
    assert g.caption_baseline_y(scene) == pytest.approx(-(scene.size.height / 2.0) + s)


def test_caption_size_fallback_without_defaults() -> None:
    from vexy_stax.scene import Scene, Size, Slide

    sc = Scene(size=Size(width=1000, height=800), slides=[Slide(src="a")])  # no caption_defaults
    assert sc.caption_defaults is None
    assert g.caption_size(sc) == pytest.approx(max(8.0, 800 * g.CAPTION_DEFAULT_SIZE_FRAC))


def test_frame_state_dict_caption_key_camelcase() -> None:
    """playwright._frame_state_dict must emit camelCase captionOpacities.

    JS stage.js reads state.captionOpacities; Python asdict() produces
    caption_opacities (snake_case). The function renames the key so per-frame
    caption fades from frame_plan reach the JS stage correctly.
    This test is ungated — _frame_state_dict is pure Python, no browser needed.
    """
    from vexy_stax.engines.playwright import _frame_state_dict

    cap_ops = [0.0, 0.5, 1.0]
    state = g.FrameState(
        camera=g.CameraPose(position=(0.0, 0.0, 1.0), target=(0.0, 0.0, 0.0), fov=60.0, near=1.0),
        gaps=[3.0, 3.0, 3.0],
        opacities=[1.0, 1.0, 1.0],
        caption_opacities=cap_ops,
    )
    d = _frame_state_dict(state)

    assert "captionOpacities" in d, "camelCase key 'captionOpacities' must be present"
    assert "caption_opacities" not in d, "snake_case key 'caption_opacities' must NOT be present"
    assert d["captionOpacities"] == cap_ops, "captionOpacities value must match input list"


def test_caption_opacities_aligned_with_slides(scene: Scene) -> None:
    """caption_opacities must return a float list length == slides for both views.

    For t=1 (expanded) all slides with show_in='expanded' must have opacity > 0;
    for t=0 (compact) they must have opacity == 0.  This verifies the contract
    consumed by _still_state in both pygfx and blender engines.
    """
    n = len(scene.slides)

    ops_exp = g.caption_opacities(scene, 1.0)
    assert isinstance(ops_exp, list) and len(ops_exp) == n
    assert all(isinstance(v, float) for v in ops_exp)
    for i, (slide, op) in enumerate(zip(scene.slides, ops_exp)):
        if slide.caption and slide.caption.show_in == "expanded":
            assert op > 0.0, f"slide {i} show_in='expanded' must be visible at t=1, got {op}"

    ops_cmp = g.caption_opacities(scene, 0.0)
    assert isinstance(ops_cmp, list) and len(ops_cmp) == n
    for i, (slide, op) in enumerate(zip(scene.slides, ops_cmp)):
        if slide.caption and slide.caption.show_in == "expanded":
            assert op == 0.0, f"slide {i} show_in='expanded' must be invisible at t=0, got {op}"


def test_plate_edge_width_scales_with_height(scene: Scene) -> None:
    """Issue 305/326: border thickness = edge.width * plate height; off (0) by default."""
    from vexy_stax.scene import Edge, Scene, Size, Slide

    # Issue 326: the showcase scene (and the default) disable the border → 0 thickness.
    assert g.plate_edge_width(scene) == pytest.approx(scene.size.height * scene.edge.width)
    assert g.plate_edge_width(scene) == pytest.approx(0.0)
    # When enabled it scales with the plate height.
    enabled = Scene(size=Size(width=1000, height=700), edge=Edge(width=0.01), slides=[Slide(src="a")])
    assert g.plate_edge_width(enabled) == pytest.approx(700 * 0.01)
    assert g.plate_edge_width(enabled) > 0


def test_reflection_constant_and_caption_plate(scene: Scene) -> None:
    """Issue 303 §1 reflection blur + issue 311 caption-plate geometry (shadows removed: 312)."""
    assert 0 < g.REFLECTION_BLUR_FRAC < 1
    assert not hasattr(g, "SHADOW_OPACITY")  # issue 312: floor shadows eliminated
    # caption plate: height = font / 0.75 (font is 75% of the plate height).
    assert g.caption_plate_height(scene) == pytest.approx(g.caption_size(scene) / 0.75)
    assert g.CAPTION_PLATE_HEIGHT_FRAC == pytest.approx(0.1 * 4 / 3)  # issue 324: font 1/3 larger (was 0.10)
    # plate sits on the ground: center = -h/2 + plate_height/2.
    assert g.caption_plate_center_y(scene) == pytest.approx(
        -(scene.size.height / 2.0) + g.caption_plate_height(scene) / 2.0
    )


def test_caption_opacities_stagger_frames() -> None:
    """Issue 309: stagger_frames steps captions back->front by N transition frames."""
    from vexy_stax.scene import Caption, CaptionFade, Scene, Size, Slide, Transition

    slides = [Slide(src=f"{i}.png", caption=Caption(text=str(i), show_in="expanded")) for i in range(6)]
    sc = Scene(
        size=Size(width=1000, height=700),
        transition=Transition(kind="expand", duration=2.0, fps=30),  # 60-frame leg
        caption_fade=CaptionFade(window=0.9, stagger_frames=6),
        slides=slides,
    )
    ops = g.caption_opacities(sc, 0.6)
    assert len(ops) == 6
    # back (i=0) leads, front (i=5) trails — monotonically non-increasing with a real spread.
    assert all(ops[i] >= ops[i + 1] - 1e-9 for i in range(5))
    assert ops[0] > ops[-1]
    # fully in only at the expanded end; fully out at compact.
    assert all(op == pytest.approx(1.0) for op in g.caption_opacities(sc, 1.0))
    assert all(op == pytest.approx(0.0) for op in g.caption_opacities(sc, 0.0))
