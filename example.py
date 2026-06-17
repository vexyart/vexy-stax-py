#!/usr/bin/env python3
# this_file: example.py
# Showcase: render compact still, expanded still, and a short transition video of
# testdata/airbl.scene.json with every available engine into outputs/<engine>/.
# Unavailable engines are skipped (not fatal). Stills are verified non-blank.

import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from vexy_stax.engines import get_engine, is_available
from vexy_stax.scene import load_scene

# Color output formatting helpers
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'

SCENE = "testdata/airbl.scene.json"
WIDTH = 1920 * 2
HEIGHT = 1240 * 2
# pygfx runs first and Blender last
ENGINES = ["pygfx", "playwright", "blender"]

def std_of(path: Path) -> float:
    with Image.open(path) as im:
        return float(np.asarray(im.convert("RGB")).std())

def main():
    # Ensure working directory is vexy-stax-py's directory
    here = Path(__file__).resolve().parent
    os.chdir(here)

    print(f"{BLUE}vexy-stax showcase — scene: {SCENE} @ {WIDTH}x{HEIGHT}{NC}")

    # Initialize benchmark reporting
    bench_file = Path("outputs/benchmark.txt")
    bench_file.parent.mkdir(parents=True, exist_ok=True)

    with open(bench_file, "w") as f:
        f.write("Vexy Stax Rendering Benchmark\n")
        f.write("=============================\n")
        f.write(f"Resolution: {WIDTH}x{HEIGHT}\n")
        f.write(f"Date: {time.ctime()}\n\n")
        f.write("Engine       | Duration (seconds)\n")
        f.write("-------------|-------------------\n")

    overall_ok = True
    summary = []

    for engine_name in ENGINES:
        print(f"\n{BLUE}=== engine: {engine_name} ==={NC}")
        
        if not is_available(engine_name):
            print(f"{YELLOW}↔ skipping {engine_name}: dependency unavailable{NC}")
            summary.append(f"{engine_name}: SKIPPED (unavailable)")
            with open(bench_file, "a") as f:
                f.write(f"{engine_name:<12} | SKIPPED\n")
            continue

        start_time = time.perf_counter()
        results = []
        
        try:
            outdir = Path(f"outputs/{engine_name}")
            outdir.mkdir(parents=True, exist_ok=True)
            engine = get_engine(engine_name)

            # We do not set VEXY_STAX_TURBO for Blender because we want HIGH QUALITY rendering.
            # Pop VEXY_STAX_TURBO from the process' environment if set.
            if "VEXY_STAX_TURBO" in os.environ:
                os.environ.pop("VEXY_STAX_TURBO")

            # --- stills -----------------------------------------------------------------
            for view in ("compact", "expanded"):
                out = outdir / f"{view}.png"
                sc = load_scene(SCENE)
                scale = WIDTH / sc.size.width
                sc.size.width, sc.size.height = WIDTH, HEIGHT
                sc.camera.gap *= scale
                if sc.caption_defaults and sc.caption_defaults.size is not None:
                    sc.caption_defaults.size *= scale
                
                engine.render_image(sc, view, out)
                
                if not out.exists() or out.stat().st_size == 0:
                    results.append((view, "FAIL", out, "(no file)"))
                    overall_ok = False
                    continue
                
                std = std_of(out)
                size = out.stat().st_size
                # Use 28.0 standard deviation threshold to match updated tests
                status = "PASS" if std > 28.0 else "FAIL"
                results.append((view, status, out, f"bytes={size} std={std:.1f}"))
                if status == "FAIL":
                    overall_ok = False

            # --- short transition video -------------------------------------------------
            out = outdir / "transition.mp4"
            sc = load_scene(SCENE)
            scale = WIDTH / sc.size.width
            sc.size.width, sc.size.height = WIDTH, HEIGHT
            sc.camera.gap *= scale
            if sc.caption_defaults and sc.caption_defaults.size is not None:
                sc.caption_defaults.size *= scale
            
            if sc.transition is None:
                results.append(("transition", "FAIL", out, "(scene has no transition)"))
                overall_ok = False
            else:
                sc.transition.kind = "expand"
                sc.transition.duration = 2.0
                sc.transition.wait = 0.0
                sc.transition.fps = 30
                sc.transition.easing = "easeInOutCubic"
                
                engine.render_video(sc, out)
                
                if out.exists() and out.stat().st_size > 0:
                    size = out.stat().st_size
                    results.append(("transition", "PASS", out, f"bytes={size}"))
                else:
                    results.append(("transition", "FAIL", out, "(no file)"))
                    overall_ok = False

        except Exception as e:
            print(f"{RED}✘ {engine_name} failed with exception: {e}{NC}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            overall_ok = False
            summary.append(f"{engine_name}: ERROR (exception)")
            with open(bench_file, "a") as f:
                f.write(f"{engine_name:<12} | ERROR\n")
            continue

        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        with open(bench_file, "a") as f:
            f.write(f"{engine_name:<12} | {elapsed:.2f}s\n")
        print(f"  Benchmark: {engine_name} finished in {elapsed:.2f}s")

        # Report results
        for view, status, path, info in results:
            if status == "PASS":
                print(f"  {GREEN}✔ {view}{NC} {path} {info}")
                summary.append(f"{engine_name}/{view}: PASS {path} {info}")
            else:
                print(f"  {RED}✘ {view}{NC} {path} {info}")
                summary.append(f"{engine_name}/{view}: FAIL {path} {info}")

    print(f"\n{BLUE}===== summary ====={NC}")
    for s in summary:
        print(f"  {s}")

    if overall_ok:
        print(f"{GREEN}✅ Showcase complete.{NC}")
    else:
        print(f"{YELLOW}⚠ Showcase finished with some failures/skips (see summary).{NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
