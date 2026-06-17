# this_file: src/vexy_stax/juicy.py
"""Per-channel linear color correction (juicy mode).

Computes corrections by comparing a Pillow overlay with a Blender stack render,
then applies the correction to the final Blender output.
"""

import os
import shutil
import subprocess
import tempfile

import cv2
import numpy as np


def compute_corrections(overlay_path: str, stack_path: str) -> list[tuple[float, float]]:
    """Compute per-channel linear color correction from Blender stack to 2D overlay.

    Returns list of 3 (scale, offset) tuples for B, G, R channels (OpenCV order).
    Correction formula: corrected[c] = pixel[c] * scale + offset
    """
    overlay_rgba = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
    stack_bgr = cv2.imread(stack_path, cv2.IMREAD_COLOR)

    if overlay_rgba is None or stack_bgr is None:
        return [(1.0, 0.0)] * 3

    # Content mask from overlay alpha (excludes floor/environment areas)
    if overlay_rgba.shape[2] >= 4:
        mask = overlay_rgba[:, :, 3] > 128
    else:
        mask = np.ones(overlay_rgba.shape[:2], dtype=bool)

    overlay_bgr = overlay_rgba[:, :, :3]

    # Resize overlay to match stack dimensions
    if overlay_bgr.shape[:2] != stack_bgr.shape[:2]:
        overlay_bgr = cv2.resize(overlay_bgr, (stack_bgr.shape[1], stack_bgr.shape[0]))
        mask = cv2.resize(mask.astype(np.uint8), (stack_bgr.shape[1], stack_bgr.shape[0])) > 0

    if mask.sum() < 100:
        return [(1.0, 0.0)] * 3

    # Per-channel mean/std matching (Reinhard color transfer)
    corrections: list[tuple[float, float]] = []
    for c in range(3):  # B, G, R
        ov = overlay_bgr[:, :, c][mask].astype(float)
        st = stack_bgr[:, :, c][mask].astype(float)
        ov_mean, ov_std = ov.mean(), max(ov.std(), 1.0)
        st_mean, st_std = st.mean(), max(st.std(), 1.0)
        scale = ov_std / st_std
        offset = ov_mean - scale * st_mean
        corrections.append((scale, offset))

    return corrections


def apply_still(image_path: str, corrections: list[tuple[float, float]]) -> None:
    """Apply per-channel linear color correction + white point normalization to a PNG."""
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        return

    result = img.astype(float)

    # Step 1: Per-channel linear correction
    for c in range(3):
        scale, offset = corrections[c]
        result[:, :, c] = result[:, :, c] * scale + offset

    # Step 2: White point — push near-white floor/env pixels to pure white
    gray = np.mean(result, axis=2)
    near_white = gray > 240
    if near_white.sum() > 100:
        for c in range(3):
            white_val = np.percentile(result[:, :, c][near_white], 95)
            if 200 < white_val < 255:
                result[:, :, c] = result[:, :, c] * (255.0 / white_val)

    cv2.imwrite(image_path, np.clip(result, 0, 255).astype(np.uint8))


def apply_video(video_path: str, corrections: list[tuple[float, float]]) -> None:
    """Apply per-channel linear color correction to video via ffmpeg curves filter."""

    def _curve(scale: float, offset: float) -> str:
        y0 = max(0.0, min(1.0, offset / 255.0))
        y1 = max(0.0, min(1.0, scale + offset / 255.0))
        return f"'0/{y0:.4f} 1/{y1:.4f}'"

    r_s, r_o = corrections[2]
    g_s, g_o = corrections[1]
    b_s, b_o = corrections[0]
    vf = f"curves=r={_curve(r_s, r_o)}:g={_curve(g_s, g_o)}:b={_curve(b_s, b_o)}"

    tmp_out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_out.close()
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            tmp_out.name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return
        shutil.move(tmp_out.name, video_path)
    finally:
        try:
            os.unlink(tmp_out.name)
        except OSError:
            pass
