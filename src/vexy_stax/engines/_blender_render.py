# this_file: src/vexy_stax/engines/_blender_render.py
"""Blender scene builder — runs INSIDE Blender's bundled Python.

Invoked as::

    blender --background --python _blender_render.py -- '{json render-job}'

It may import ONLY modules available in Blender's Python: ``bpy``, ``mathutils``,
``sys``, ``json``, ``math``, ``os``, ``subprocess``, ``shutil``, ``tempfile``.
It must NOT import ``vexy_stax`` or any pip package.

All view geometry is precomputed by ``vexy_stax.geometry`` in the parent process
and handed over as a FLAT render-job. This script is a "dumb" renderer: it places
plates at the given world coordinates, points the camera at the given pose, and
sets per-plate material alpha — keyframing everything for video. See the schema
in ``blender.py`` (``_build_job``) for the exact job shape.

World conventions (mirror ``vexy_stax.geometry``):
- Plates stand upright with their bottom edge on the floor at ``Z = 0``,
  horizontally centered on ``X``, stacked along ``-Z`` (index 0 farthest).
- ``+Y`` points toward the viewer.
- Plate width/height in points == source-image pixel dimensions.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def parse_job() -> dict:
    """Extract the JSON render-job passed after ``--`` in argv."""
    argv = sys.argv
    if "--" not in argv:
        print("Error: no '--' separator found in argv", file=sys.stderr)
        sys.exit(1)
    return json.loads(argv[argv.index("--") + 1])


# ---------------------------------------------------------------------------
# Scene scaffolding
# ---------------------------------------------------------------------------


def clear_scene() -> None:
    """Remove all default objects and orphan datablocks."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert ``#rrggbb`` to linear-ish 0..1 RGB (sRGB values, good enough)."""
    text = hex_color.lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    try:
        r = int(text[0:2], 16) / 255.0
        g = int(text[2:4], 16) / 255.0
        b = int(text[4:6], 16) / 255.0
    except (ValueError, IndexError):
        return (1.0, 1.0, 1.0)
    return (r, g, b)


def setup_renderer(job: dict) -> None:
    """Configure renderer: Eevee for turbo mode, Cycles otherwise."""
    scene = bpy.context.scene

    if job.get("turbo"):
        # Eevee: real-time, dramatically faster than Cycles. Engine name varies
        # across Blender versions (BLENDER_EEVEE_NEXT in 4.2+/5.x).
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = max(1, int(job.get("samples", 16)))
    else:
        scene.render.engine = "CYCLES"
        # High quality but FEASIBLE (issue 320 §8): OpenImageDenoise + adaptive sampling
        # keep a low sample count clean for these flat, unlit plates, so the showcase no
        # longer takes ~100 min. (Was 64 samples + 32 bounces ≈ 52 s/frame on CPU.)
        scene.cycles.samples = int(job.get("samples", 16))
        scene.cycles.use_denoising = True
        if hasattr(scene.cycles, "use_adaptive_sampling"):
            scene.cycles.use_adaptive_sampling = True
            # Aggressive adaptive threshold: these flat, evenly-lit plates converge in very few
            # samples, and OIDN cleans the rest, so most pixels stop early (issue 325 speedup).
            scene.cycles.adaptive_threshold = 0.02
            scene.cycles.adaptive_min_samples = 4
        if hasattr(scene.cycles, "denoiser"):
            scene.cycles.denoiser = "OPENIMAGEDENOISE"

        # Shallow LIGHT bounces — the plates are flat and unlit/emissive, so indirect light adds
        # almost nothing; deep recursion is pure cost (issue 325 speedup). Transparent bounces
        # (the pass-through stack) are kept high below — those are what the compact view needs.
        scene.cycles.max_bounces = 4
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 2
        scene.cycles.transmission_bounces = 4
        # Transparent bounces: in the COMPACT view every plate stacks head-on, so a single
        # camera ray crosses ALL of them. Each plate is a SOLIDIFY slab (2 faces) and may have
        # a mirrored reflection (2 more), so a ray can cross ~4*N transparent surfaces before it
        # reaches the opaque backdrop. If the budget is exhausted Cycles returns BLACK — which is
        # exactly the "black where it should be pink" regression (issue 325). Transparent bounces
        # are cheap pass-throughs, so we keep a generous margin above 4*N (floor 64).
        n_plates = len(job.get("plates", []))
        scene.cycles.transparent_max_bounces = max(64, n_plates * 4)
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for device in prefs.devices:
                device.use = True
            scene.cycles.device = "GPU"
        except (KeyError, AttributeError, RuntimeError):
            pass  # CPU fallback

    scene.render.resolution_x = int(job["width"])
    scene.render.resolution_y = int(job["height"])
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

    # Standard color management: reproduce input sRGB colors faithfully.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


def setup_world(job: dict) -> None:
    """Uniformly-lit environment using the scene background color."""
    color = _hex_to_rgb(job.get("background", "#ffffff"))
    world = bpy.data.worlds.new("VexyStaxWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    bg = tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    output = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(bg.outputs["Background"], output.inputs["Surface"])


def floor_y_of(job: dict) -> float:
    """World ``Y`` of the floor line: the bottom edge of the tallest plate.

    Plates are vertically centered at ``Y = 0`` (height along ``Y``), so the tallest
    plate's bottom edge — the virtual ground the deck stands on — is at ``Y = -max_h/2``.
    The smoked-glass floor and the mirror reflections (flipped across this line) both
    reference it, matching the JS/pygfx engines (``floor_y = -tallest/2``).
    """
    max_h = max((float(p["height"]) for p in job.get("plates", [])), default=806.0)
    return -max_h / 2.0


def create_floor(job: dict) -> object:
    """Smoked-glass floor plane in the XZ plane at the floor line (issue 303 §1).

    A barely-visible (``floor.opacity`` ~4%) alpha-blended pane tinted ``floor.color``,
    *not* a reflective BSDF — Eevee screen-space reflections are unreliable, so the
    reflections are explicit mirror plates (see ``create_reflection``) rendered *under*
    this pane. The material is an unlit emission-style shader so the tint reads the same
    in Eevee and Cycles and the reflections show through. Footprint/placement mirror the
    pygfx/JS floor so all engines frame the deck identically.
    """
    floor_cfg = job.get("floor", {})
    color = _hex_to_rgb(floor_cfg.get("color", "#1a1a1a"))
    opacity = float(floor_cfg.get("opacity", 0.04))

    floor_y = floor_y_of(job)

    # Footprint: match pygfx/JS (width = widest*4, depth = stack_depth + widest*2),
    # centered under the deck at (0, floor_y, -depth/2). Fall back to a large square.
    plates = job.get("plates", [])
    widest = max((float(p["width"]) for p in plates), default=640.0)
    depth = float(job.get("floor_extent", 0.0))
    extent_w = widest * 4.0
    extent_z = (depth + widest * 2.0) if depth > 0 else widest * 2.0

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, floor_y, -depth / 2.0), rotation=(math.pi / 2.0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale = (extent_w, extent_z, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    mat = _make_unlit_material("FloorMat", color, opacity)
    # The smoked pane sits ABOVE the reflections in draw order so reflections show
    # *through* it (render_order: reflections -1, floor 0, plates default).
    floor.data.materials.append(mat)
    return floor


def _make_unlit_material(name: str, color: tuple, alpha: float) -> object:
    """Create an alpha-blended, unlit (emission) material at ``color``/``alpha``.

    Used for the smoked floor, plate borders and the caption plates (fill/border/text):
    an Emission shader keeps the color flat/uniform (no scene lighting needed) and renders
    identically in Eevee (turbo) and Cycles. Alpha is driven by a Transparent/Emission mix
    so ``alpha`` controls visibility; returns the material (alpha set via ``set_unlit_alpha``).
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    if hasattr(mat, "shadow_method"):
        mat.shadow_method = "NONE"
    mat.use_backface_culling = False

    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    mix = tree.nodes.new("ShaderNodeMixShader")
    # Mix factor == alpha: 0 -> fully transparent, 1 -> full emission color.
    mix.inputs["Fac"].default_value = max(0.0, min(1.0, alpha))
    tree.links.new(transparent.outputs[0], mix.inputs[1])
    tree.links.new(emission.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], out.inputs["Surface"])
    # Stash the mix node so callers can keyframe alpha (mix.inputs["Fac"]).
    mat["_alpha_node"] = mix.name
    return mat


def set_unlit_alpha(mat: object, value: float, frame: int | None = None) -> None:
    """Set (and optionally keyframe) an unlit material's alpha (its Mix ``Fac``)."""
    mix = mat.node_tree.nodes[mat["_alpha_node"]]
    mix.inputs["Fac"].default_value = max(0.0, min(1.0, value))
    if frame is not None:
        mix.inputs["Fac"].keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------------------
# Plates
# ---------------------------------------------------------------------------


def create_plate(plate_job: dict, index: int) -> tuple[object, object]:
    """Create one upright textured plate. Returns ``(object, alpha_math_node)``.

    Coordinate convention (three.js / SCENE.md §1, §8 — matched by
    ``vexy_stax.geometry``): width along ``X``, height along ``Y`` *centered at
    ``Y = 0``* (the vertical middle of the tallest slide), thin along ``Z`` with
    the face normal pointing ``+Z`` toward the viewer. Plates are stacked along
    ``Z`` (set by ``place_plates``); index 0 farthest (most ``-Z``), front at
    ``Z = 0``. The floor sits just below ``Y = -h/2``.
    """
    w = float(plate_job["width"])
    h = float(plate_job["height"])
    img_path = plate_job["path"]

    # Default plane lies in the XY plane with normal +Z — exactly the face we
    # want toward the +Z camera. Scale to width (X) and height (Y), centered at 0.
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    plate = bpy.context.active_object
    plate.name = f"Plate_{index:02d}"
    plate.scale = (w / 2.0, h / 2.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    # Default plane UVs already read upright and un-mirrored from a +Z camera
    # whose look-at basis is right-handed (right=+X, up=+Y): image column 0 maps
    # to plate -X, which the camera sees at screen-left. No UV flip — flipping
    # here mirrors the artwork horizontally.

    # 1pt thickness extending away from the camera (-Z).
    solidify = plate.modifiers.new("Solidify", "SOLIDIFY")
    solidify.thickness = 1.0
    solidify.offset = -1

    # ---- Material: image color + (image alpha * opacity) ----
    mat = bpy.data.materials.new(f"PlateMat_{index:02d}")
    mat.use_nodes = True
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    if hasattr(mat, "shadow_method"):
        mat.shadow_method = "HASHED"
    mat.use_backface_culling = False

    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.0

    tex_node = tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(img_path)
    tex_node.location = (-600, 300)
    tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    # alpha = image_alpha * opacity, via a MULTIPLY node we keyframe per frame.
    math_node = tree.nodes.new("ShaderNodeMath")
    math_node.operation = "MULTIPLY"
    math_node.location = (-300, 200)
    tree.links.new(tex_node.outputs["Alpha"], math_node.inputs[0])
    tree.links.new(math_node.outputs[0], bsdf.inputs["Alpha"])
    math_node.inputs[1].default_value = 1.0

    plate.data.materials.append(mat)
    return plate, math_node


def create_reflection(plate_job: dict, index: int) -> tuple[object, object] | None:
    """Mirror copy of a plate for the floor reflection (issue 303 §1).

    Returns ``(object, alpha_math_node)`` or ``None`` when reflections are disabled
    (``reflection_path`` absent). The mesh is the same upright plate textured with the
    *Gaussian-blurred* reflection PNG (precomputed CLI-side in ``blender.py`` with radius
    ``REFLECTION_BLUR_FRAC × image_h_px``), then flipped across the floor line by negating
    the Y scale (``scale.y = -1``) — exactly like the JS/pygfx engines. Its alpha is
    ``image_alpha × (plate_opacity × reflectivity)``, keyframed via the returned node; it
    renders behind/under the smoked floor so the floor tints it. The blur is the key
    requirement — the reflection looks soft, not a crisp mirror.
    """
    refl_path = plate_job.get("reflection_path")
    if not refl_path:
        return None

    w = float(plate_job["width"])
    h = float(plate_job["height"])

    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    refl = bpy.context.active_object
    refl.name = f"Reflection_{index:02d}"
    # scale.y < 0 mirrors the image vertically across the plate center; place_plates then
    # positions the center at 2*floor_y - plate_center_y so it sits below the floor line.
    refl.scale = (w / 2.0, -h / 2.0, 1.0)
    # Do NOT apply the negative scale (that bakes the flip into the mesh and re-mirrors);
    # keep it live so the object reads as a flipped image, matching scale.y=-1 elsewhere.

    mat = bpy.data.materials.new(f"ReflMat_{index:02d}")
    mat.use_nodes = True
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    if hasattr(mat, "shadow_method"):
        mat.shadow_method = "NONE"
    mat.use_backface_culling = False

    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.0
    # Emit the blurred color so it reads uniformly (no dependence on scene lighting),
    # consistent with the unlit floor/plates look in turbo Eevee.
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = 1.0

    tex_node = tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(refl_path)
    tex_node.location = (-600, 300)
    tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    if "Emission Color" in bsdf.inputs:
        tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Emission Color"])

    # alpha = image_alpha * (plate_opacity * reflectivity); the (opacity*reflectivity)
    # factor is keyframed per frame via input[1] (set by set_plate_alpha).
    math_node = tree.nodes.new("ShaderNodeMath")
    math_node.operation = "MULTIPLY"
    math_node.location = (-300, 200)
    tree.links.new(tex_node.outputs["Alpha"], math_node.inputs[0])
    tree.links.new(math_node.outputs[0], bsdf.inputs["Alpha"])
    math_node.inputs[1].default_value = 0.0

    refl.data.materials.append(mat)
    # Draw reflections first so the smoked floor (and plates) composite over them.
    refl.show_transparent = True
    return refl, math_node


def create_border(plate_job: dict, job: dict, index: int) -> tuple[object, object] | None:
    """Thin rectangular frame around a plate (issue 305). Returns ``(object, material)``.

    Built as ONE mesh of 4 thin filled quads tracing the plate's rectangular perimeter
    (top/bottom/left/right strips), thickness ``edge.width`` (scene points, == plate-mesh
    units). Filled quads (not 1px GL lines) so the border is thickness-controllable and
    visible regardless of the plate image's transparency. Unlit/emissive in ``edge.color``
    so it reads as a clean frame. Returns ``None`` when ``edge.width <= 0`` (border off).
    The mesh is centered at the origin like the plate; ``place_plates`` tracks the plate Z.
    """
    edge_cfg = job.get("edge", {})
    width = float(edge_cfg.get("width", 0.0))
    if width <= 0.0:
        return None
    color = _hex_to_rgb(edge_cfg.get("color", "#cccccc"))

    w = float(plate_job["width"])
    h = float(plate_job["height"])
    hw, hh = w / 2.0, h / 2.0
    t = width  # border thickness in plate-mesh units

    # Build 4 strips as quads. Top/bottom span the full width and sit just inside the
    # top/bottom edges; left/right fill the gap between them so corners are square.
    # Slightly in front of the plate (+Z) so the frame is never z-fought/hidden.
    zf = max(0.5, t * 0.25)
    verts: list = []
    faces: list = []

    def _quad(x0: float, y0: float, x1: float, y1: float) -> None:
        base = len(verts)
        verts.extend([(x0, y0, zf), (x1, y0, zf), (x1, y1, zf), (x0, y1, zf)])
        faces.append((base, base + 1, base + 2, base + 3))

    _quad(-hw, hh - t, hw, hh)  # top
    _quad(-hw, -hh, hw, -hh + t)  # bottom
    _quad(-hw, -hh + t, -hw + t, hh - t)  # left (between top/bottom strips)
    _quad(hw - t, -hh + t, hw, hh - t)  # right

    mesh = bpy.data.meshes.new(f"BorderMesh_{index:02d}")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    border = bpy.data.objects.new(f"Border_{index:02d}", mesh)
    bpy.context.scene.collection.objects.link(border)

    mat = _make_unlit_material(f"BorderMat_{index:02d}", color, 1.0)
    border.data.materials.append(mat)
    return border, mat


# ---------------------------------------------------------------------------
# Captions (issue 311): white opaque bordered plate + centered text.
# Floor shadows were removed (issue 312): plates cast NO shadow.
# ---------------------------------------------------------------------------


def _text_unlit_material(name: str, color: tuple) -> object:
    """Unlit/emissive material for caption text (flat ``color``), alpha-keyframeable.

    Reuses ``_make_unlit_material`` so the text reads as a clean flat color (no scene
    lighting) and its alpha is driven by the same Mix ``Fac`` node as the fill/border —
    so ``set_caption_alpha`` fades fill + border + text together (issue 311).
    """
    return _make_unlit_material(name, color, 1.0)


def _build_caption_text(text: str, size: float, color: tuple, font_value: str, index: int) -> object:
    """Create a CENTERED (H+V) Blender text object at the origin sized ``size`` world units.

    The text size equals the caption size directly (1em == size, scene-point world units).
    Returns the text object (origin at its visual center via ``align_x/y == CENTER``).
    """
    bpy.ops.object.text_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = f"CaptionText_{index:02d}"
    obj.data.body = text
    # Center the text block both ways so its object origin is its visual center; placing
    # the object at the plate center then centers the text in the plate (issue 311).
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = max(8.0, size)

    # Best-effort font loading: if the value looks like an existing file path, load it into
    # Blender's font library; otherwise fall back to the built-in default.
    if font_value and os.path.isfile(font_value):
        try:
            obj.data.font = bpy.data.fonts.load(font_value)
        except Exception as exc:  # noqa: BLE001
            print(f"Caption font load failed ({font_value!r}): {exc}", file=sys.stderr)

    mat = _text_unlit_material(f"CaptionTextMat_{index:02d}", color)
    obj.data.materials.append(mat)
    return obj


def create_caption(plate_job: dict, job: dict, index: int) -> tuple[object, list] | None:
    """Build a caption as a white opaque bordered PLATE with centered text (issue 311).

    Returns ``(group_obj, [materials])`` or ``None`` when the slide has no caption. The
    group's LOCAL origin is the caption plate's LEFT edge at its vertical center (issue 332
    relayout — captions are LEFT-aligned with their slide); the plate spans local X in
    ``[0, width]`` and Y in ``[-h/2, +h/2]``. ``place_plates`` sets the group to
    ``(caption_anchor_x, caption_plate_center_y, plate_z)`` so the plate's LEFT edge sits at
    the anchor X (the slide left edge), its vertical center at center_y, and it recedes with
    its plate.

    Components (all parented to the group, all unlit/emissive, all alpha-keyframed together):
    - fill: a solid white (#ffffff) OPAQUE plane covering the rectangle;
    - border: 4 thin quads of ``edge.width`` in ``edge.color`` framing the rectangle
      (same as the slide plates, issue 305);
    - text: the caption string at ``size`` (1em), in the caption color, H+V centered.

    Width = measured typeset text width + 2 × ``caption_pad_em`` × size (1.5em pad each
    side). Height = ``caption_plate_height``. The whole group fades with the per-frame
    caption opacity via ``set_caption_alpha`` (0 in compact, 1 in expanded).
    """
    caption = plate_job.get("caption")
    if not caption or not caption.get("text"):
        return None

    text = caption["text"]
    size = float(caption.get("size") or 28.0)
    text_color = _hex_to_rgb(caption.get("color") or "#222222")
    font_value = caption.get("font") or ""

    plate_h = float(job.get("caption_plate_height", size / 0.75))
    pad_em = float(job.get("caption_pad_em", 1.5))
    edge_cfg = job.get("edge", {})
    edge_w = float(edge_cfg.get("width", 0.0))
    edge_hex = edge_cfg.get("color", "#cccccc")
    # Caption plate fill + border colors (issue 324): independently overridable, each
    # defaulting to the slide edge color (so fill == border == slide border by default).
    fill_color = _hex_to_rgb(job.get("caption_fill_color") or edge_hex)
    border_color = _hex_to_rgb(job.get("caption_border_color") or edge_hex)

    # --- Text first, so we can measure its typeset width to size the plate ---
    text_obj = _build_caption_text(text, size, text_color, font_value, index)
    # Text dimensions are only valid after the dependency graph is evaluated.
    bpy.context.view_layer.update()
    text_w = float(text_obj.dimensions.x)
    # Plate width = measured text width + 1.5em pad on EACH side (issue 311).
    width = text_w + 2.0 * pad_em * size
    hh = plate_h / 2.0

    # --- Group empty: local origin = plate RIGHT edge at vertical center ---
    group = bpy.data.objects.new(f"Caption_{index:02d}", None)
    bpy.context.scene.collection.objects.link(group)

    mats: list = []

    # --- Fill: solid opaque plane in the SAME color as the border/edge (issue 320 §7) ---
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    fill = bpy.context.active_object
    fill.name = f"CaptionFill_{index:02d}"
    fill.scale = (width / 2.0, hh, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    # Issue 332: LEFT-edge local origin → the plate spans X in [0, width]; center at +width/2.
    fill.location = (width / 2.0, 0.0, 0.0)
    fill_mat = _make_unlit_material(f"CaptionFillMat_{index:02d}", fill_color, 1.0)
    fill.data.materials.append(fill_mat)
    fill.parent = group
    mats.append(fill_mat)

    # --- Border: 4 thin quads framing X in [-width, 0], Y in [-hh, hh] ---
    if edge_w > 0.0:
        zf = max(0.5, edge_w * 0.25)  # nudge in front so the frame is never z-fought
        t = edge_w
        verts: list = []
        faces: list = []

        def _quad(x0: float, y0: float, x1: float, y1: float) -> None:
            base = len(verts)
            verts.extend([(x0, y0, zf), (x1, y0, zf), (x1, y1, zf), (x0, y1, zf)])
            faces.append((base, base + 1, base + 2, base + 3))

        # Issue 332: LEFT-edge origin → quads frame X in [0, width], Y in [-hh, hh].
        _quad(0.0, hh - t, width, hh)  # top
        _quad(0.0, -hh, width, -hh + t)  # bottom
        _quad(0.0, -hh + t, t, hh - t)  # left
        _quad(width - t, -hh + t, width, hh - t)  # right
        mesh = bpy.data.meshes.new(f"CaptionBorderMesh_{index:02d}")
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        border = bpy.data.objects.new(f"CaptionBorder_{index:02d}", mesh)
        bpy.context.scene.collection.objects.link(border)
        border_mat = _make_unlit_material(f"CaptionBorderMat_{index:02d}", border_color, 1.0)
        border.data.materials.append(border_mat)
        border.parent = group
        mats.append(border_mat)

    # --- Text: centered in the plate (X = +width/2 with LEFT-edge origin), in front of fill ---
    text_obj.location = (width / 2.0, 0.0, max(1.0, edge_w * 0.5))
    text_obj.parent = group
    mats.append(text_obj.data.materials[0])

    return group, mats


def set_caption_alpha(caption: tuple, value: float, frame: int | None = None) -> None:
    """Set (and optionally keyframe) the WHOLE caption plate's alpha (fill+border+text).

    ``caption`` is ``(group_obj, [materials])`` from :func:`create_caption`; every material
    is an unlit material whose alpha is its Mix ``Fac`` node, so the fill, border and text
    fade together with the per-frame caption opacity (issue 311). At opacity 0 the entire
    plate is invisible.
    """
    _group, mats = caption
    for mat in mats:
        set_unlit_alpha(mat, value, frame=frame)


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------


def create_camera() -> object:
    cam_data = bpy.data.cameras.new("VexyStaxCamera")
    cam_data.clip_end = 1_000_000.0
    cam_obj = bpy.data.objects.new("VexyStaxCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def _look_at_euler(location: Vector, target: Vector):
    """Rotation euler that points the camera ``-Z`` from ``location`` to ``target``.

    World up is ``+Y`` (the deck's vertical axis; see ``create_plate``).
    """
    forward = (target - location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    if abs(forward.dot(world_up)) > 0.999:
        world_up = Vector((0.0, 0.0, 1.0))
    right = forward.cross(world_up).normalized()
    up = right.cross(forward).normalized()
    rot = Matrix(
        (
            (right.x, up.x, -forward.x),
            (right.y, up.y, -forward.y),
            (right.z, up.z, -forward.z),
        )
    )
    return rot.to_euler()


def _fov_to_lens(fov_deg: float, sensor_width: float = 36.0) -> float:
    """Horizontal FOV (degrees) -> focal length (mm) for the given sensor width."""
    fov = math.radians(fov_deg)
    return sensor_width / (2.0 * math.tan(fov / 2.0))


def apply_camera_frame(cam_obj: object, frame_job: dict, frame: int | None = None) -> None:
    """Place the camera from a frame-job pose; keyframe when ``frame`` given."""
    cam = frame_job["camera"]
    location = Vector(cam["position"])
    target = Vector(cam["target"])
    cam_obj.location = location
    cam_obj.rotation_euler = _look_at_euler(location, target)
    cam_obj.data.sensor_fit = "HORIZONTAL"
    cam_obj.data.sensor_width = 36.0
    cam_obj.data.lens = _fov_to_lens(float(cam["fov"]))
    cam_obj.data.clip_start = max(0.001, float(cam.get("near", 1.0)))
    if frame is not None:
        cam_obj.keyframe_insert(data_path="location", frame=frame)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        cam_obj.data.keyframe_insert(data_path="lens", frame=frame)


# ---------------------------------------------------------------------------
# Placement: convert per-frame gaps -> world Z positions
# ---------------------------------------------------------------------------


def plate_z_positions(gaps: list[float]) -> list[float]:
    """World ``Z`` per plate from inter-plate gaps (index 0 farthest, at most -Z).

    ``gaps[i]`` is the spacing in front of plate ``i`` (mirrors geometry.py's
    ``plate_gaps``: ``gaps[0]`` is unused, the deck spans ``[-stack_depth, 0]``).
    Plate 0 sits at ``-stack_depth``; the front plate sits at ``Z = 0``.
    """
    n = len(gaps)
    if n == 0:
        return []
    stack_depth = sum(gaps[1:])
    positions = [0.0]
    for i in range(1, n):
        positions.append(positions[-1] + gaps[i])
    # positions currently measure distance-from-back; shift so front plate is 0.
    return [p - stack_depth for p in positions]


def place_plates(
    plates: list,
    captions: list,
    gaps: list[float],
    anchor_x: float,
    center_y: float,
    floor_y: float,
    slide_lift: float = 0.0,
    reflections: list | None = None,
    borders: list | None = None,
    frame: int | None = None,
) -> None:
    """Set (and optionally keyframe) plate + caption-plate + decoration positions for a frame.

    Plates are LIFTED to ``(0, slide_lift, z)`` (issue 332: each slide sits on top of its
    on-floor caption plate; ``slide_lift`` is one caption-plate height, or 0 when captions are
    off). Caption plates have their LEFT edge at ``anchor_x`` (the slide left edge) and their
    vertical CENTER at ``center_y`` (on the floor), recessed to the plate's ``Z`` (issue 311).
    Reflections sit at ``(0, 2*floor_y - slide_lift, z)`` — the lifted plate center mirrored
    across the floor line, with their material flipping the image (issue 303 §1). Borders track
    the lifted plate at ``(0, slide_lift, z)`` (issue 305). ``anchor_x``/``center_y``/``floor_y``
    are already in mesh coordinate space. Floor shadows were removed (issue 312).
    """
    z_positions = plate_z_positions(gaps)
    for plate, z in zip(plates, z_positions, strict=True):
        plate.location = (0.0, slide_lift, z)
        if frame is not None:
            plate.keyframe_insert(data_path="location", frame=frame)
    for cap, z in zip(captions, z_positions, strict=True):
        if cap is None:
            continue
        group = cap[0]
        # The caption-plate group's local origin is the plate's RIGHT edge at its vertical
        # center, so X = anchor_x puts the right edge on the anchor, Y = center_y puts the
        # vertical center at center_y, and Z = the plate's stacked position (recedes with it).
        group.location = (anchor_x, center_y, z)
        if frame is not None:
            group.keyframe_insert(data_path="location", frame=frame)
    if reflections is not None:
        for refl, z in zip(reflections, z_positions, strict=True):
            if refl is None:
                continue
            # Plate center is Y=slide_lift; its mirror across the floor line is 2*floor_y - lift.
            refl[0].location = (0.0, 2.0 * floor_y - slide_lift, z)
            if frame is not None:
                refl[0].keyframe_insert(data_path="location", frame=frame)
    if borders is not None:
        for border, z in zip(borders, z_positions, strict=True):
            if border is None:
                continue
            border[0].location = (0.0, slide_lift, z)
            if frame is not None:
                border[0].keyframe_insert(data_path="location", frame=frame)


def set_plate_alpha(node: object, value: float, frame: int | None = None) -> None:
    node.inputs[1].default_value = max(0.0, min(1.0, value))
    if frame is not None:
        node.inputs[1].keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------------------
# Bezier easing (proven Blender-version-compat handling)
# ---------------------------------------------------------------------------


def _apply_bezier_to_action(action) -> None:
    def _apply(fcurves) -> None:
        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"

    if hasattr(action, "layers"):  # Blender 5.x layered actions
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    _apply(cb.fcurves)
    elif hasattr(action, "fcurves"):  # Blender 3.x/4.x
        _apply(action.fcurves)


def _set_bezier(obj) -> None:
    if getattr(obj, "animation_data", None) and obj.animation_data.action:
        _apply_bezier_to_action(obj.animation_data.action)


def set_bezier_everywhere(
    plates: list,
    captions: list,
    mats_nodes: list,
    cam_obj: object,
    reflections: list | None = None,
    borders: list | None = None,
) -> None:
    """Apply BEZIER to every animated datablock for smooth motion."""
    _set_bezier(cam_obj)
    _set_bezier(cam_obj.data)
    for plate in plates:
        _set_bezier(plate)
        for mat in plate.data.materials:
            _set_bezier(mat.node_tree)
    # Caption is (group_obj, [materials]): the group's position and each material's alpha
    # (fill/border/text) are keyframed per frame, so smooth the group and every node_tree.
    for cap in captions:
        if cap is None:
            continue
        group, mats = cap
        _set_bezier(group)
        for mat in mats:
            if mat is not None and getattr(mat, "node_tree", None) is not None:
                _set_bezier(mat.node_tree)
    # Reflection/border alphas + positions are also keyframed per frame; smooth them too so
    # the decorations fade/move in step with their plates (issues 303/305). item[0] is the
    # object; item[1] is a node (reflections) or a material (borders) — either way the
    # keyframed fcurves live on the object's material node_trees, so iterate uniformly.
    for group_list in (reflections, borders):
        if not group_list:
            continue
        for item in group_list:
            if item is None:
                continue
            obj = item[0]
            _set_bezier(obj)
            for mat in obj.data.materials:
                if mat is not None and getattr(mat, "node_tree", None) is not None:
                    _set_bezier(mat.node_tree)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _apply_decoration_alphas(
    job: dict,
    opacities: list[float],
    refl_nodes: list,
    borders: list,
    frame: int | None = None,
) -> None:
    """Set (and optionally keyframe) reflection/border alphas from plate opacities.

    Reflection alpha factor = plate_opacity × reflectivity; border alpha = plate_opacity
    (so the frame fades with its plate). Both fade with the plate's per-frame opacity
    (issues 303/305). Floor shadows were removed (issue 312).
    """
    reflectivity = float(job.get("floor", {}).get("reflectivity", 0.5))
    for node, alpha in zip(refl_nodes, opacities, strict=True):
        if node is not None:
            set_plate_alpha(node, alpha * reflectivity, frame=frame)
    for border, alpha in zip(borders, opacities, strict=True):
        if border is not None:
            set_unlit_alpha(border[1], alpha, frame=frame)


def render_still(
    job: dict,
    cam_obj,
    plates,
    captions,
    alpha_nodes,
    anchor_x: float,
    center_y: float,
    floor_y: float,
    slide_lift: float,
    reflections,
    refl_nodes,
    borders,
) -> None:
    """Render a single-frame still from the one frame in the job."""
    frame_job = job["frames"][0]
    apply_camera_frame(cam_obj, frame_job)
    place_plates(
        plates,
        captions,
        frame_job["gaps"],
        anchor_x,
        center_y,
        floor_y,
        slide_lift,
        reflections=reflections,
        borders=borders,
    )
    opacities = frame_job["opacities"]
    for node, alpha in zip(alpha_nodes, opacities, strict=True):
        set_plate_alpha(node, alpha)
    for cap, ca in zip(captions, frame_job["caption_opacities"], strict=True):
        if cap is not None:
            set_caption_alpha(cap, ca)
    _apply_decoration_alphas(job, opacities, refl_nodes, borders)

    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = job["output"]
    bpy.ops.render.render(write_still=True)


def render_animation(
    job: dict,
    cam_obj,
    plates,
    captions,
    alpha_nodes,
    anchor_x: float,
    center_y: float,
    floor_y: float,
    slide_lift: float,
    reflections,
    refl_nodes,
    borders,
) -> None:
    """Keyframe every frame, render a PNG sequence, assemble with ffmpeg."""
    frames = job["frames"]
    total = len(frames)
    for fi, frame_job in enumerate(frames, start=1):
        apply_camera_frame(cam_obj, frame_job, frame=fi)
        place_plates(
            plates,
            captions,
            frame_job["gaps"],
            anchor_x,
            center_y,
            floor_y,
            slide_lift,
            reflections=reflections,
            borders=borders,
            frame=fi,
        )
        opacities = frame_job["opacities"]
        for node, alpha in zip(alpha_nodes, opacities, strict=True):
            set_plate_alpha(node, alpha, frame=fi)
        for cap, ca in zip(captions, frame_job["caption_opacities"], strict=True):
            if cap is not None:
                set_caption_alpha(cap, ca, frame=fi)
        _apply_decoration_alphas(job, opacities, refl_nodes, borders, frame=fi)

    set_bezier_everywhere(
        plates,
        captions,
        alpha_nodes,
        cam_obj,
        reflections=reflections,
        borders=borders,
    )

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total
    scene.render.fps = int(job.get("fps", 30))
    frame_dir = tempfile.mkdtemp(prefix="vexy_stax_frames_")
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(frame_dir, "frame_")
    bpy.ops.render.render(animation=True)
    assemble_video(frame_dir, job["output"], int(job.get("fps", 30)))


def assemble_video(frame_dir: str, output_path: str, fps: int) -> None:
    """Combine the rendered PNG sequence into an MP4 via ffmpeg."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        os.path.join(frame_dir, "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(frame_dir, ignore_errors=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    job = parse_job()

    clear_scene()
    setup_renderer(job)
    setup_world(job)
    create_floor(job)

    # The parent process (blender.py) computed caption_anchor_x from geometry in
    # scene-coordinate units (same space as scene.size).  _blender_render.py scales
    # plate meshes by (scene.size.width / widest_image_px), so we must apply the
    # same scale to anchor_x so captions stay aligned with the scaled plates.
    #
    # Mesh scale: create_plate uses plate_job["width"] = info["width"] * scale,
    # and plate_job["height"] = info["height"] * scale, where scale = scene_width /
    # widest_image_px.  caption_anchor_x is already in those same scaled units
    # because geometry.caption_anchor_x uses scene.size.width directly — so no
    # additional multiplication is needed here; the value passes through unchanged.
    anchor_x: float = float(job.get("caption_anchor_x", 0.0))
    # Caption-plate vertical center Y (issue 311); same scene-coordinate units as the
    # scaled plate meshes, so it passes through unchanged (see anchor_x note above).
    center_y: float = float(job.get("caption_plate_center_y", 0.0))
    # Issue 332: vertical lift added to every slide plate so it sits on top of its on-floor
    # caption plate (0 when captions are off). Same scene-coordinate units as the scaled meshes.
    slide_lift: float = float(job.get("slide_lift", 0.0))

    floor_y = floor_y_of(job)

    plates: list = []
    captions: list = []  # (group_obj, [materials]) | None per plate (issue 311)
    alpha_nodes: list = []
    reflections: list = []  # (obj, alpha_node) | None per plate (issue 303 §1)
    refl_nodes: list = []  # alpha_node | None per plate (parallel to reflections)
    borders: list = []  # (obj, mat) | None per plate (issue 305)
    for i, plate_job in enumerate(job["plates"]):
        plate, alpha_node = create_plate(plate_job, i)
        plates.append(plate)
        alpha_nodes.append(alpha_node)
        captions.append(create_caption(plate_job, job, i))

        refl = create_reflection(plate_job, i)
        reflections.append(refl)
        refl_nodes.append(refl[1] if refl is not None else None)
        borders.append(create_border(plate_job, job, i))

    cam_obj = create_camera()

    if job.get("video"):
        render_animation(
            job,
            cam_obj,
            plates,
            captions,
            alpha_nodes,
            anchor_x,
            center_y,
            floor_y,
            slide_lift,
            reflections,
            refl_nodes,
            borders,
        )
    else:
        render_still(
            job,
            cam_obj,
            plates,
            captions,
            alpha_nodes,
            anchor_x,
            center_y,
            floor_y,
            slide_lift,
            reflections,
            refl_nodes,
            borders,
        )

    print(f"Render complete: {job['output']}")


if __name__ == "__main__":
    main()
