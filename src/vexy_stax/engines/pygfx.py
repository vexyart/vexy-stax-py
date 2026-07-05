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
reflection (``floor.reflectivity``). Plates cast NO floor shadow (issue 312 — the
shadow rendering was removed). Captions (issue 311) are small WHITE OPAQUE bordered
PLATES placed to the LEFT of their plate: a white quad framed by a thin border in
``scene.edge.color`` (same thickness as the slide-plate edges) with the caption text
centered on top. The plate's right edge aligns to ``geo.caption_anchor_x(scene)`` and
its vertical center to ``geo.caption_plate_center_y(scene)`` (both × the deck scale),
at the plate's current Z. The whole caption plate (fill + border + text) fades together
with ``geo.caption_opacities`` / ``FrameState.caption_opacities`` — no local
re-derivation.

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


def _box_blur_1d(arr: np.ndarray, radius: int, axis: int) -> np.ndarray:
    """Separable moving-average blur of a float array along ``axis``.

    Uses a cumulative-sum sliding window (edge-replicated) so the cost is O(N)
    per axis regardless of the radius. ``radius`` is the half-window in pixels.
    """
    if radius < 1:
        return arr
    arr = np.moveaxis(arr, axis, 0)
    n = arr.shape[0]
    # Pad by replicating edge rows so the window never wraps or darkens borders.
    pad = np.concatenate([arr[:1].repeat(radius, axis=0), arr, arr[-1:].repeat(radius, axis=0)], axis=0)
    cumsum = np.cumsum(pad, axis=0)
    # Window sum over [i, i+2*radius] == cumsum[i+2r] - cumsum[i-1]; prepend a zero row.
    zero = np.zeros_like(cumsum[:1])
    cumsum = np.concatenate([zero, cumsum], axis=0)
    win = 2 * radius + 1
    out = (cumsum[win : win + n] - cumsum[0:n]) / float(win)
    return np.moveaxis(out, 0, axis)


def _gaussian_blur_rgba(arr: np.ndarray, radius: float) -> np.ndarray:
    """Approximate a Gaussian blur of an RGBA uint8 image (issue 303 §1, blurry reflections).

    scipy is not a dependency here, so we approximate the Gaussian with three passes of a
    separable box blur (the central-limit theorem makes repeated box blurs converge to a
    Gaussian). ``radius`` is the blur radius in pixels (``REFLECTION_BLUR_FRAC`` × plate
    image height). Premultiplies alpha before blurring so transparent pixels don't bleed
    dark color into the soft reflection, then un-premultiplies. Returns a contiguous uint8
    RGBA array; a radius < 1 returns the input unchanged (still a copy).
    """
    if radius < 1:
        return np.ascontiguousarray(arr)
    # Reflections are soft, so blur a DOWNSCALED copy (the GPU upsamples the small blurred
    # texture smoothly). This keeps the relative blur identical while avoiding a costly
    # full-resolution multi-pass blur on large plates (e.g. 6234x4030) — ~100x faster.
    h, w = arr.shape[:2]
    max_side = 512
    scale = min(1.0, max_side / float(max(h, w)))
    if scale < 1.0:
        sw, sh = max(1, round(w * scale)), max(1, round(h * scale))
        arr = np.ascontiguousarray(np.asarray(Image.fromarray(arr, "RGBA").resize((sw, sh), Image.Resampling.LANCZOS)))
        radius = radius * scale
    r = max(1, int(round(radius)))
    f = arr.astype(np.float32) / 255.0
    rgb = f[..., :3]
    a = f[..., 3:4]
    premult = rgb * a  # premultiply so the blur weights color by coverage
    chans = np.concatenate([premult, a], axis=2)
    # Box-blur radius per pass so three passes give ~the requested Gaussian sigma.
    pass_r = max(1, int(round(r / 1.5)))
    for _ in range(3):
        chans = _box_blur_1d(chans, pass_r, axis=0)
        chans = _box_blur_1d(chans, pass_r, axis=1)
    out_a = chans[..., 3:4]
    safe_a = np.where(out_a > 1e-4, out_a, 1.0)
    out_rgb = np.clip(chans[..., :3] / safe_a, 0.0, 1.0)  # un-premultiply
    out = np.concatenate([out_rgb, np.clip(out_a, 0.0, 1.0)], axis=2)
    return np.ascontiguousarray((out * 255.0 + 0.5).astype(np.uint8))


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


# pygfx renders captions with its OWN bundled font unless the requested family is registered
# with its font manager — and that fallback reads heavier/bolder than the intended face (327).
# So register font files on demand and resolve the default family to the bundled TTF.
_registered_font_families: dict[str, str] = {}

# Aliases that all mean "the bundled default caption font" (issue 328: vexy-stax.ttf ==
# Zalando Sans Expanded; the JS engine pulls the matching "Zalando Sans" wdth125/wght500 from
# Google Fonts). Any of these (or an unset font) resolves to the bundled TTF so pygfx renders it.
_DEFAULT_FONT_ALIASES = frozenset({"vexy-stax", "vexy stax", "zalando sans", "zalando sans expanded"})


def _register_font(path: str) -> str | None:
    """Register a TTF/OTF with pygfx's font manager; return its family name (cached)."""
    fam = _registered_font_families.get(path)
    if fam is not None:
        return fam
    try:
        ff = gfx.font_manager.add_font_file(path)
    except Exception:  # noqa: BLE001 — bad/missing font file → fall back to the default
        return None
    family = str(ff.family)
    _registered_font_families[path] = family
    return family


def _caption_font_family(font_value: str | None) -> str | None:
    """Resolve a caption font (a family name or a TTF/OTF path) to a pygfx family name.

    A filesystem path is registered on the fly and resolved to its own family. An unset font or
    a default-font alias (issue 328: "Zalando Sans"/"vexy-stax"/…) maps to the bundled
    ``vexy-stax.ttf`` so pygfx renders it (not its heavier built-in fallback). Unknown family
    names are returned as-is (host fonts).
    """
    if not font_value or font_value.strip().lower() in _DEFAULT_FONT_ALIASES:
        p = geo.default_font_path()
        resolved = _register_font(str(p)) if p is not None else None
        return resolved or font_value or None
    if Path(font_value).is_file():
        return _register_font(font_value)
    return font_value


def _pygfx_fov_deg(hfov_deg: float, aspect: float) -> float:
    """pygfx camera ``fov`` whose frustum's HORIZONTAL fov equals ``hfov_deg``.

    pygfx (unlike three.js/Blender) builds its frustum as ``size = 2*near*tan(fov/2)``
    then ``height = 2*size/(1+aspect)``, ``width = height*aspect`` — so its ``fov`` is a
    width+height *mean*, not a vertical fov. Feeding it the three.js vertical fov makes
    pygfx render ~``(1+aspect)/2`` too zoomed. We invert pygfx's formula: take the
    three.js vertical half-tan (``tan(hfov/2)/aspect``) and solve for the pygfx ``fov``
    that yields the same frustum height (and thus the same horizontal fov). Valid when
    the camera aspect equals the render aspect (true here), so pygfx's
    ``maintain_aspect`` adjustment is a no-op.
    """
    tan_v = math.tan(math.radians(hfov_deg) / 2.0) / aspect
    return math.degrees(2.0 * math.atan(tan_v * (1.0 + aspect) / 2.0))


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
        self._borders: list[list[gfx.Mesh]] = []
        # Per-slide caption plate: a list of meshes (white quad + border bars) plus the
        # centered text, or None when the slide has no caption (issue 311).
        self._captions: list[list[gfx.WorldObject] | None] = []

        tallest = 0
        arrays: list[np.ndarray] = []
        for slide in scene.slides:
            arr = _load_rgba(slide.src)
            arrays.append(arr)
            h, w = arr.shape[0], arr.shape[1]
            self._sizes.append((w, h))
            tallest = max(tallest, h)

        widest = max(w for w, _ in self._sizes) if self._sizes else 1
        self._scale = scene.size.width / widest
        self._floor_y = -(tallest * self._scale) / 2.0

        reflectivity = scene.floor.reflectivity
        # Border thickness in world units (issue 305). The deck is scaled so the widest
        # plate spans scene.size.width world units (and, aspect preserved, the tallest spans
        # scene.size.height) — i.e. scene-point units already ARE world units here, so the
        # geometry helpers are used directly (NO extra × self._scale, which would shrink the
        # border/captions ~5x whenever scene.size differs from the source pixels).
        self._edge_w = geo.plate_edge_width(scene)
        edge_rgb = _hex_to_rgb(scene.edge.color)

        for index, (slide, arr, (w, h)) in enumerate(zip(scene.slides, arrays, self._sizes, strict=True)):
            w_scaled = w * self._scale
            h_scaled = h * self._scale
            plate = gfx.Mesh(gfx.plane_geometry(w_scaled, h_scaled), self._make_image_material(arr))
            self.world.add(plate)
            self._plates.append(plate)

            if reflectivity > 0:
                # Blurry reflection (issue 303 §1): mirror copy with a Gaussian-BLURRED
                # texture so the reflection is soft, not a crisp mirror. Blur radius is a
                # fraction of the plate IMAGE height in pixels (sharp plate keeps `arr`).
                blurred = _gaussian_blur_rgba(arr, geo.REFLECTION_BLUR_FRAC * h)
                refl_mat = self._make_image_material(blurred)
                refl_mat.depth_write = False  # under the glass; don't occlude floor/plates
                refl = gfx.Mesh(gfx.plane_geometry(w_scaled, h_scaled), refl_mat)
                refl.local.scale = (1.0, -1.0, 1.0)  # flip across the floor line
                refl.render_order = -2  # behind/under the floor
                self.world.add(refl)
                self._reflections.append(refl)
            else:
                self._reflections.append(None)  # type: ignore[arg-type]

            self._borders.append(self._make_border(w_scaled, h_scaled, edge_rgb))
            self._captions.append(self._make_caption(scene, slide, edge_rgb, index))

        self._add_floor(scene, tallest * self._scale)

        aspect = scene.size.width / scene.size.height
        self.camera = gfx.PerspectiveCamera(_pygfx_fov_deg(scene.camera.fov, aspect), aspect)

    @staticmethod
    def _make_image_material(arr: np.ndarray) -> gfx.MeshBasicMaterial:
        """A double-sided, alpha-blended textured material for a plate."""
        mat = gfx.MeshBasicMaterial(map=gfx.Texture(arr, dim=2))
        mat.alpha_mode = "blend"
        mat.side = "both"
        return mat

    def _make_border(self, w: float, h: float, rgb: tuple[float, float, float]) -> list[gfx.Mesh]:
        """Four thin filled quads framing a plate's rectangle (issue 305).

        Returns ``[]`` when ``edge.width == 0`` (border disabled). Otherwise builds top,
        bottom, left and right bars of thickness ``self._edge_w`` (scene-point border ×
        scale) in ``edge.color`` — solid filled meshes, NOT 1px GL lines, so the frame is
        thickness-controllable and shows regardless of plate transparency. The bars are
        positioned in the plate's local plane (centered at the origin); ``set_frame`` parents
        them to each plate's per-frame ``(0, 0, z)`` so the frame tracks the plate every
        frame. The left/right bars overlap the corners (full height) so the frame is seamless.
        """
        t = self._edge_w
        if t <= 0.0:
            return []
        hw, hh = w / 2.0, h / 2.0
        bars: list[gfx.Mesh] = []
        # (width, height, center_x, center_y): top, bottom span full width; sides full height.
        specs = (
            (w, t, 0.0, hh - t / 2.0),  # top
            (w, t, 0.0, -hh + t / 2.0),  # bottom
            (t, h, -hw + t / 2.0, 0.0),  # left
            (t, h, hw - t / 2.0, 0.0),  # right
        )
        for bw, bh, cx, cy in specs:
            mat = gfx.MeshBasicMaterial(color=rgb)
            mat.alpha_mode = "blend"
            mat.side = "both"
            bar = gfx.Mesh(gfx.plane_geometry(bw, bh), mat)
            # Local offset within the plate plane; nudged toward +Z so it sits ON the plate
            # face (avoids z-fighting with the textured plate at the same Z).
            bar.local.position = (cx, cy, 0.0)
            bar.render_order = 1
            bar._vexy_offset = (cx, cy)  # type: ignore[attr-defined]
            self.world.add(bar)
            bars.append(bar)
        return bars

    def _add_floor(self, scene: Scene, tallest: float) -> None:
        """A (smoked-glass) floor plane just below the tallest plate (issue 303 §1).

        Rendered at ``floor.color``/``floor.opacity`` (default ~4% — barely visible smoked
        glass). ``render_order = 0`` puts it ABOVE the mirror reflection (order −2) but it
        does not write depth, so the soft reflection shows THROUGH the translucent glass
        rather than being occluded. Plates cast no floor shadow (issue 312).
        """
        depth = geo.stack_depth(scene, "expanded")
        widest = max(w for w, _ in self._sizes) * self._scale
        extent_w = widest * 4.0
        extent_z = (depth + widest * 2.0) if depth > 0 else widest * 2.0
        mat = gfx.MeshBasicMaterial(color=_hex_to_rgb(scene.floor.color))
        mat.opacity = scene.floor.opacity
        mat.alpha_mode = "blend"
        mat.depth_write = False  # let the reflection beneath show through the smoked glass
        floor = gfx.Mesh(gfx.plane_geometry(extent_w, extent_z), mat)
        floor.local.position = (0.0, self._floor_y, -depth / 2.0)
        floor.local.rotation = la.quat_from_axis_angle((1.0, 0.0, 0.0), -math.pi / 2.0)
        floor.render_order = 0
        self.world.add(floor)

    def _make_caption(
        self, scene: Scene, slide: Slide, edge_rgb: tuple[float, float, float], index: int
    ) -> list[gfx.WorldObject] | None:
        """Build a small WHITE OPAQUE bordered caption PLATE for a slide (issue 311).

        Returns ``None`` when the slide has no caption. Otherwise builds a group of meshes
        (returned as a flat list) all expressed in a LOCAL frame whose origin is the plate's
        RIGHT edge at its vertical center; ``set_frame`` translates this origin to
        ``(caption_anchor_x × scale, caption_plate_center_y × scale, plate_z)`` each frame and
        fades the whole group together with ``state.caption_opacities[i]``. Pieces:

        * a solid WHITE (#ffffff) quad — the caption plate fill;
        * four thin border bars in ``scene.edge.color`` of thickness ``self._edge_w`` (same as
          the slide-plate edges), framing the quad;
        * the caption text (font size ``caption_size`` × scale, color = per-slide style over
          ``caption_defaults.color`` else ``#222222``), horizontally + vertically CENTERED.

        Plate height is ``geo.caption_plate_height(scene)`` and width is the measured typeset
        text width + ``2 × CAPTION_PLATE_PAD_EM × caption_size`` (1.5em pad each side), all ×
        ``self._scale`` so the plate matches the deck scale.
        """
        # Issue 332: a global captions=false toggle skips ALL caption plates.
        if not scene.captions or slide.caption is None:
            return None
        style = _caption_style(scene, slide)
        # Scene-point units already ARE world units (the deck is scaled so scene.size maps to
        # world), so the geometry caption helpers are used directly — no extra × self._scale.
        size = float(style.size) if style and style.size else geo.caption_size(scene)
        color = (style.color if style and style.color else None) or "#222222"
        # Resolve to a pygfx-registered family name (issue 327: the bundled REM, not the
        # heavier built-in fallback). Falls back to None → pygfx default when unresolvable.
        font = _caption_font_family(style.font if style and style.font else None)
        plate_h = geo.caption_plate_height(scene)
        pad = geo.CAPTION_PLATE_PAD_EM * size  # 1.5em pad per side, in world units

        # Build the text first so we can measure its typeset width (pygfx computes the text
        # geometry's bounding box lazily on first access — accurate to the chosen font_size).
        kwargs: dict = dict(
            text=slide.caption.text,
            font_size=size,
            anchor="middle-center",
            material=gfx.TextMaterial(color=color),
        )
        if font is not None:
            kwargs["family"] = font
        text = gfx.Text(**kwargs)
        text.material.alpha_mode = "blend"
        bb = text.get_bounding_box()
        text_w = float(bb[1][0] - bb[0][0]) if bb is not None else 0.0

        plate_w = text_w + 2.0 * pad
        # Local frame: origin at the plate's LEFT edge & vertical center (issue 332 relayout —
        # captions are now LEFT-aligned with their slide), so the plate spans X in [0, plate_w]
        # and Y in [-plate_h/2, +plate_h/2]. center is at (+plate_w/2, 0).
        cx = plate_w / 2.0

        pieces: list[gfx.WorldObject] = []

        # Caption plates are alpha-blended (so they can fade), which means pygfx paints them in
        # render_order rather than depth-occluding. With a single GLOBAL order, every caption's
        # text drew over every caption's fill, so neighbouring captions bled through each other
        # (issue 327). Give each caption a CONTIGUOUS order block that increases with the slide
        # index (front plates = higher index = painted last), so a front caption's opaque fill
        # fully covers the captions behind it. Base 10 keeps captions above plates/borders.
        cap_order = 10 + index * 3

        # Caption plate fill + border colors (issue 324): independently overridable, each
        # defaulting to the slide edge color (so by default fill == border == slide border).
        fill_rgb = _hex_to_rgb(geo.caption_fill_color(scene))
        border_rgb = _hex_to_rgb(geo.caption_border_color(scene))

        # Fill quad in the caption fill color (default = the edge color).
        fill_mat = gfx.MeshBasicMaterial(color=fill_rgb)
        fill_mat.alpha_mode = "blend"
        fill_mat.side = "both"
        fill = gfx.Mesh(gfx.plane_geometry(plate_w, plate_h), fill_mat)
        fill.render_order = cap_order
        fill._vexy_offset = (cx, 0.0)  # type: ignore[attr-defined]
        fill._vexy_dz = 0.0  # type: ignore[attr-defined]
        self.world.add(fill)
        pieces.append(fill)

        # Border bars (top/bottom full width, left/right full height) — reuse the slide-edge
        # thickness so the caption frame matches the plate frame (issue 311).
        t = self._edge_w
        if t > 0.0:
            hw, hh = plate_w / 2.0, plate_h / 2.0
            specs = (
                (plate_w, t, cx, hh - t / 2.0),  # top
                (plate_w, t, cx, -hh + t / 2.0),  # bottom
                (t, plate_h, cx - hw + t / 2.0, 0.0),  # left
                (t, plate_h, cx + hw - t / 2.0, 0.0),  # right
            )
            for bw, bh, bx, by in specs:
                bmat = gfx.MeshBasicMaterial(color=border_rgb)
                bmat.alpha_mode = "blend"
                bmat.side = "both"
                bar = gfx.Mesh(gfx.plane_geometry(bw, bh), bmat)
                bar.render_order = cap_order + 1
                bar._vexy_offset = (bx, by)  # type: ignore[attr-defined]
                bar._vexy_dz = max(t * 0.5, 1e-3)  # type: ignore[attr-defined]
                self.world.add(bar)
                pieces.append(bar)

        # Centered text on top of this caption's own plate (issue 327: text is in the caption's
        # own order block, so it never paints over a *different* caption's fill).
        text.render_order = cap_order + 2
        text._vexy_offset = (cx, 0.0)  # type: ignore[attr-defined]
        text._vexy_dz = max(t, 1e-3)  # type: ignore[attr-defined]
        self.world.add(text)
        pieces.append(text)
        return pieces

    def set_frame(self, state: geo.FrameState) -> None:
        """Place plates/captions and the camera for one frame state.

        Caption opacity comes exclusively from ``state.caption_opacities`` (populated
        by ``geometry.frame_plan`` for video and by ``geo.caption_opacities`` for stills
        via ``_still_state``). Each caption plate's LEFT edge anchors at
        ``caption_anchor_x`` (the slide left edge, issue 332) and its vertical center at
        ``caption_plate_center_y`` (on the floor); its Z tracks the plate's Z so the caption
        recedes with its plate in expanded view (issue 311). Plates cast no floor shadow (312).
        """
        z_positions = geo._stack_positions(state.gaps)
        reflectivity = self.scene.floor.reflectivity
        # Tiny forward nudge keeps the border on the front face of its plate (no z-fight).
        border_dz = max(self._edge_w * 0.5, 1e-3)
        # Caption-plate anchor in world units (scene points == world units): right edge X
        # and vertical center Y. Used directly (no × self._scale — see _make_caption).
        cap_anchor_x = geo.caption_anchor_x(self.scene)
        cap_center_y = geo.caption_plate_center_y(self.scene)
        # Issue 332: lift every slide plate (+ its border/reflection) by one caption-plate
        # height so it sits ON TOP of its on-floor caption plate (0 when captions are off).
        lift = geo.slide_lift(self.scene)
        for i in range(len(self.scene.slides)):
            z = z_positions[i]
            alpha = state.opacities[i]
            plate = self._plates[i]
            plate.local.position = (0.0, lift, z)
            plate.material.opacity = alpha

            refl = self._reflections[i]
            if refl is not None:
                # Mirror the lifted plate center across the floor line (Y = floor_y): a point
                # at Y = lift maps to 2*floor_y - lift.
                refl.local.position = (0.0, 2.0 * self._floor_y - lift, z)
                refl.material.opacity = alpha * reflectivity

            # Plate border: track this plate's lifted center every frame; fade with it (305).
            for bar in self._borders[i]:
                cx, cy = bar._vexy_offset  # type: ignore[attr-defined]
                bar.local.position = (cx, cy + lift, z + border_dz)
                bar.material.opacity = alpha

            # Caption plate (issue 311): anchor the group at the right-edge/center anchor at
            # the plate's Z; fill + border + text all fade together with the caption opacity.
            cap = self._captions[i]
            if cap is not None:
                cap_alpha = state.caption_opacities[i]
                for piece in cap:
                    ox, oy = piece._vexy_offset  # type: ignore[attr-defined]
                    dz = piece._vexy_dz  # type: ignore[attr-defined]
                    piece.local.position = (cap_anchor_x + ox, cap_center_y + oy, z + dz)
                    piece.material.opacity = cap_alpha

        pose = state.camera
        aspect = self.scene.size.width / self.scene.size.height
        self.camera.fov = _pygfx_fov_deg(pose.fov, aspect)
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
        im = im.resize((width, height), Image.Resampling.LANCZOS)
    return im


def _still_state(scene: Scene, view: View) -> geo.FrameState:
    """The single FrameState for a still in ``view`` (t=0 compact, t=1 expanded)."""
    if view == "expanded":
        camera = geo.expanded_camera(scene)
        gaps = geo.plate_gaps(scene)
        t = 1.0
    else:
        camera = geo.compact_camera(scene)
        gaps = [geo.MIN_GAP for _ in scene.slides]
        t = 0.0
    opacities = [s.resolved_opacity(view) for s in scene.slides]
    caption_ops = geo.caption_opacities(scene, t)
    return geo.FrameState(camera=camera, gaps=gaps, opacities=opacities, caption_opacities=caption_ops)


class PygfxEngine:
    """Fast GPU off-screen renderer (SPEC.md §5.3)."""

    name = "pygfx"

    def render_image(self, scene: Scene, view: View, out: Path) -> None:
        """Render a single still of SCENE in VIEW (compact|expanded) to a PNG."""
        deck = _Deck(scene)
        deck.set_frame(_still_state(scene, view))
        im = _render_frame(deck, scene.size.width, scene.size.height, _SUPERSAMPLE)
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "PNG")

    def render_video(self, scene: Scene, out: Path) -> None:
        """Render SCENE's transition to an mp4 (requires ``scene.transition``).

        Video params come from ``scene.video`` (issue 335 §3): the encode fps is
        ``geo.video_fps``, the render size is ``geo.video_dimensions`` (defaults to
        ``scene.size``), and the frame plan is bookended by held first/last stills
        (``geo.frame_plan`` honours ``scene.video.first_hold``/``last_hold``).
        """
        if scene.transition is None:
            raise ValueError("scene has no transition; nothing to animate (use render_image)")
        _require_ffmpeg()
        plan = geo.frame_plan(scene)
        if not plan:
            raise ValueError("transition produced no frames")

        width, height = geo.video_dimensions(scene)
        fps = geo.video_fps(scene)
        deck = _Deck(scene)
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="vexy_stax_pygfx_") as tmp:
            tmp_dir = Path(tmp)
            for i, state in enumerate(plan):
                deck.set_frame(state)
                # No supersample for video frames: many frames, speed matters.
                im = _render_frame(deck, width, height, 1)
                im.convert("RGB").save(tmp_dir / f"frame_{i:05d}.png", "PNG")
            _encode_video(tmp_dir, fps, out)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg finished but {out} is missing/empty")


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise an actionable error."""
    found = shutil.which("ffmpeg")
    if not found:
        raise FileNotFoundError("ffmpeg not found on PATH. Install with: brew install ffmpeg")
    return found


def _encode_video(frame_dir: Path, fps: int, out: Path) -> None:
    """Assemble a PNG sequence into an H.264 mp4 with ffmpeg.

    Hardware-decoder-safe encode (issue 334): the pygfx frames have hard aliased edges
    that, with B-frames + a single IDR keyframe, made macOS VideoToolbox (QuickTime /
    QuickLook) desync ~40 % in and stay corrupted for the rest of the clip (ffmpeg's
    software decoder tolerated it; playwright/blender's smoother frames did not trip it).
    So: ``-bf 0`` (no B-frames), a keyframe every ``fps`` frames (``-g``/``-keyint_min``)
    so any desync self-heals within a second, and explicit bt709 / limited-range color
    tags so VideoToolbox interprets the stream correctly.
    """
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
        "-profile:v",
        "high",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-bf",
        "0",
        "-g",
        str(max(1, fps)),
        "-keyint_min",
        str(max(1, fps)),
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
        "-movflags",
        "+faststart",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{tail}")


register(PygfxEngine())
