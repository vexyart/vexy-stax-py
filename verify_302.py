#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["scikit-image", "pillow", "numpy"]
# ///
# this_file: verify_302.py
"""Issue-302 cross-engine verification: examine first+last video frames + stills.

After ``python example.py`` renders ``outputs/<engine>/{compact.png,expanded.png,
transition.mp4}`` for blender/pygfx/playwright, this:
  1. extracts the FIRST and LAST frame of each engine's transition.mp4 (ffmpeg),
  2. gates every image non-blank (std>28 AND uniq>500),
  3. SSIM-compares the same kind across engines (same composition), and
  4. writes side-by-side montages (compact / expanded / first-frame / last-frame)
     to outputs/_compare/ for eyeballing.
Exit 0 only if every present image passes the blank gate and every cross-engine
pair clears the loose SSIM threshold (same layout despite shading/AA differences).
"""

from __future__ import annotations

import subprocess
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
CMP = OUT / "_compare"
ENGINES = ["blender", "pygfx", "playwright"]
W, H = 640, 414
SSIM_THRESHOLD = 0.40


def ffmpeg_frame(video: Path, dst: Path, *, last: bool) -> bool:
    """Extract the first (or last) frame of ``video`` to ``dst``. Returns success."""
    if not video.exists() or video.stat().st_size == 0:
        return False
    if last:
        # -sseof seeks from the end; grab the final frame.
        cmd = ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(video), "-update", "1", "-frames:v", "1", str(dst)]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(video), "-frames:v", "1", "-update", "1", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 0


def load_rgb(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB").resize((W, H), Image.LANCZOS)
    return np.asarray(im, dtype=np.uint8)


def gate(arr: np.ndarray) -> tuple[float, int, bool]:
    std = float(arr.std())
    uniq = int(np.unique(arr.reshape(-1, 3), axis=0).shape[0])
    return std, uniq, std > 28.0 and uniq > 500


def montage(images: list[tuple[str, np.ndarray]], dst: Path) -> None:
    """Horizontal labelled montage of (label, arr) tiles."""
    if not images:
        return
    pad = 4
    tiles = [a for _, a in images]
    total_w = sum(t.shape[1] for t in tiles) + pad * (len(tiles) + 1)
    canvas = np.full((H + pad * 2, total_w, 3), 255, dtype=np.uint8)
    x = pad
    for _, t in images:
        canvas[pad : pad + H, x : x + t.shape[1]] = t
        x += t.shape[1] + pad
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(dst)


def main() -> int:
    CMP.mkdir(parents=True, exist_ok=True)
    kinds = ["compact", "expanded", "first", "last"]
    imgs: dict[str, dict[str, np.ndarray]] = {k: {} for k in kinds}
    ok = True

    print("=" * 72)
    print("BLANK GATE")
    print("=" * 72)
    for eng in ENGINES:
        d = OUT / eng
        # stills
        for kind in ("compact", "expanded"):
            p = d / f"{kind}.png"
            if p.exists():
                imgs[kind][eng] = load_rgb(p)
        # video frames
        video = d / "transition.mp4"
        for kind, last in (("first", False), ("last", True)):
            dst = CMP / f"{eng}-{kind}.png"
            if ffmpeg_frame(video, dst, last=last):
                imgs[kind][eng] = load_rgb(dst)
        for kind in kinds:
            if eng in imgs[kind]:
                std, uniq, g = gate(imgs[kind][eng])
                tag = "PASS" if g else "FAIL"
                ok = ok and g
                print(f"  {eng:>11} {kind:<9} std={std:6.2f} uniq={uniq:6d}  {tag}")
            else:
                print(f"  {eng:>11} {kind:<9} (missing)")

    print("\n" + "=" * 72)
    print(f"CROSS-ENGINE SSIM (loose >= {SSIM_THRESHOLD} = same composition)")
    print("=" * 72)
    worst = 1.0
    for kind in kinds:
        present = [e for e in ENGINES if e in imgs[kind]]
        for a, b in combinations(present, 2):
            s = float(ssim(imgs[kind][a], imgs[kind][b], channel_axis=2, data_range=255))
            worst = min(worst, s)
            mark = "OK" if s >= SSIM_THRESHOLD else "LOW"
            if s < SSIM_THRESHOLD:
                ok = False
            print(f"  {kind:<9} {a:>11} <-> {b:<11} ssim={s:.4f}  [{mark}]")

    for kind in kinds:
        montage([(e, imgs[kind][e]) for e in ENGINES if e in imgs[kind]], CMP / f"montage-{kind}.png")
    print(f"\nmontages written to {CMP}")
    print(f"worst cross-engine SSIM = {worst:.4f}")
    print(f"OVERALL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
