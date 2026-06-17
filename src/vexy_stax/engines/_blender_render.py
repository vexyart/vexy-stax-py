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
        scene.cycles.samples = int(job.get("samples", 128))
        scene.cycles.use_denoising = True
        # Each plate has 2 faces (Solidify); a ray through N transparent plates
        # needs ~2*N bounces. Default 8 is too few for decks of 5+ plates.
        n_plates = len(job.get("plates", []))
        scene.cycles.transparent_max_bounces = max(16, n_plates * 4)
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


def create_floor(job: dict) -> object:
    """Reflective floor plane in the XZ plane, just below the tallest plate.

    Plates are vertically centered at ``Y = 0`` (height along ``Y``), so the
    tallest plate's bottom edge is at ``Y = -max_h/2``. The floor sits 3pt below
    that (SCENE.md §1).
    """
    floor_cfg = job.get("floor", {})
    color = _hex_to_rgb(floor_cfg.get("color", "#f2f2f2"))
    reflectivity = float(floor_cfg.get("reflectivity", 0.5))

    max_h = max((float(p["height"]) for p in job.get("plates", [])), default=806.0)
    floor_y = -max_h / 2.0 - 3.0

    # Footprint large enough to dwarf the deck (default XY plane is horizontal at
    # +Z up; we want it horizontal in XZ, so rotate 90° about X).
    depth = float(job.get("floor_extent", 30000.0))
    floor_extent = max(30000.0, depth * 3.0)
    bpy.ops.mesh.primitive_plane_add(size=floor_extent, location=(0, floor_y, 0), rotation=(math.pi / 2.0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"

    mat = bpy.data.materials.new("FloorMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    # reflectivity 0..1 -> roughness 0.6..0.0 (more reflective = smoother).
    bsdf.inputs["Roughness"].default_value = max(0.0, 0.6 * (1.0 - reflectivity))
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.5
    floor.data.materials.append(mat)
    return floor


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


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------


def create_caption(plate_job: dict, index: int) -> tuple[object, object] | None:
    """Create a text object centered beneath the plate, or ``None`` if no caption.

    Returns ``(object, material)``; the material's emission alpha is keyframed to
    fade with the caption's per-frame opacity.
    """
    caption = plate_job.get("caption")
    if not caption or not caption.get("text"):
        return None

    text = caption["text"]
    size = float(caption.get("size") or 28.0)
    color = _hex_to_rgb(caption.get("color") or "#222222")

    bpy.ops.object.text_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = f"Caption_{index:02d}"
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "TOP"
    # Caption font height: scale to be readable relative to the plate height.
    obj.data.size = max(8.0, size * (float(plate_job["height"]) / 806.0))

    # Text lies in its local XY plane facing +Z by default — same facing as the
    # plates (toward the viewer). No rotation needed; it is positioned beneath the
    # plate by ``place_plates``, which reads the stashed plate height.
    obj["_plate_h"] = float(plate_job["height"])

    mat = bpy.data.materials.new(f"CaptionMat_{index:02d}")
    mat.use_nodes = True
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = 1.0
    obj.data.materials.append(mat)
    return obj, mat


def set_caption_alpha(mat: object, value: float, frame: int | None = None) -> None:
    """Set (and optionally keyframe) a caption material's alpha."""
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = max(0.0, min(1.0, value))
    if frame is not None:
        bsdf.inputs["Alpha"].keyframe_insert("default_value", frame=frame)


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


def place_plates(plates: list, captions: list, gaps: list[float], frame: int | None = None) -> None:
    """Set (and optionally keyframe) plate + caption stacking positions for a frame.

    Plates are centered at ``(0, 0, z)`` (height along ``Y`` centered at 0,
    stacked along ``Z``). Captions sit beneath each plate's bottom edge.
    """
    z_positions = plate_z_positions(gaps)
    for plate, z in zip(plates, z_positions, strict=True):
        plate.location = (0.0, 0.0, z)
        if frame is not None:
            plate.keyframe_insert(data_path="location", frame=frame)
    for cap, z in zip(captions, z_positions, strict=True):
        if cap is None:
            continue
        obj = cap[0]
        plate_h = float(obj.get("_plate_h", 806.0))
        obj.location = (0.0, -plate_h / 2.0 - obj.data.size * 0.5, z)
        if frame is not None:
            obj.keyframe_insert(data_path="location", frame=frame)


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


def set_bezier_everywhere(plates: list, captions: list, mats_nodes: list, cam_obj: object) -> None:
    """Apply BEZIER to every animated datablock for smooth motion."""
    _set_bezier(cam_obj)
    _set_bezier(cam_obj.data)
    for plate in plates:
        _set_bezier(plate)
        for mat in plate.data.materials:
            _set_bezier(mat.node_tree)
    for cap in captions:
        if cap is not None:
            _set_bezier(cap[1].node_tree)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def render_still(job: dict, cam_obj, plates, captions, alpha_nodes) -> None:
    """Render a single-frame still from the one frame in the job."""
    frame_job = job["frames"][0]
    apply_camera_frame(cam_obj, frame_job)
    place_plates(plates, captions, frame_job["gaps"])
    for node, alpha in zip(alpha_nodes, frame_job["opacities"], strict=True):
        set_plate_alpha(node, alpha)
    for cap, ca in zip(captions, frame_job["caption_opacities"], strict=True):
        if cap is not None:
            set_caption_alpha(cap[1], ca)

    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = job["output"]
    bpy.ops.render.render(write_still=True)


def render_animation(job: dict, cam_obj, plates, captions, alpha_nodes) -> None:
    """Keyframe every frame, render a PNG sequence, assemble with ffmpeg."""
    frames = job["frames"]
    total = len(frames)
    for fi, frame_job in enumerate(frames, start=1):
        apply_camera_frame(cam_obj, frame_job, frame=fi)
        place_plates(plates, captions, frame_job["gaps"], frame=fi)
        for node, alpha in zip(alpha_nodes, frame_job["opacities"], strict=True):
            set_plate_alpha(node, alpha, frame=fi)
        for cap, ca in zip(captions, frame_job["caption_opacities"], strict=True):
            if cap is not None:
                set_caption_alpha(cap[1], ca, frame=fi)

    set_bezier_everywhere(plates, captions, alpha_nodes, cam_obj)

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

    plates: list = []
    captions: list = []
    alpha_nodes: list = []
    for i, plate_job in enumerate(job["plates"]):
        plate, alpha_node = create_plate(plate_job, i)
        plates.append(plate)
        alpha_nodes.append(alpha_node)
        captions.append(create_caption(plate_job, i))

    cam_obj = create_camera()

    if job.get("video"):
        render_animation(job, cam_obj, plates, captions, alpha_nodes)
    else:
        render_still(job, cam_obj, plates, captions, alpha_nodes)

    print(f"Render complete: {job['output']}")


if __name__ == "__main__":
    main()
