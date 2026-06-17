#!/usr/bin/env python3
# this_file: repro_blender.py
# Minimal repro: render blender stills mirroring example.py's showcase scaling, at a
# configurable target width, to isolate whether the "black middle" bug is geometry-scale
# or pixel-resolution dependent.
import os, sys, time
from pathlib import Path
from vexy_stax.engines import get_engine
from vexy_stax.scene import load_scene

os.chdir(Path(__file__).resolve().parent)
os.environ.pop("VEXY_STAX_TURBO", None)

scene_path = sys.argv[1] if len(sys.argv) > 1 else "testdata/airbl.scene.json"
view = sys.argv[2] if len(sys.argv) > 2 else "compact"
target_w = int(sys.argv[3]) if len(sys.argv) > 3 else 3840

sc = load_scene(scene_path)
# Mirror example.py scaling
scale = target_w / sc.size.width
target_h = round(sc.size.height * scale)
sc.size.width, sc.size.height = target_w, target_h
sc.camera.gap *= scale
if sc.caption_defaults and sc.caption_defaults.size is not None:
    sc.caption_defaults.size *= scale

out = Path(f"outputs/repro/blender_{view}_{target_w}.png")
out.parent.mkdir(parents=True, exist_ok=True)
eng = get_engine("blender")
t = time.perf_counter()
eng.render_image(sc, view, out)  # type: ignore[arg-type]
import numpy as np
from PIL import Image
std = float(np.asarray(Image.open(out).convert("RGB")).std())
print(f"rendered {view}@{target_w}x{target_h} in {time.perf_counter()-t:.1f}s -> {out} ({out.stat().st_size} bytes) std={std:.1f}")
