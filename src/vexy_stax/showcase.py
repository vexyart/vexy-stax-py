# this_file: src/vexy_stax/showcase.py
"""Showcase / benchmark runner ported from ``example.py`` (issue 335 §1).

The per-engine render loop, the near-blank std gate, the benchmark file and the sibling
JS-demo rebuild all used to live inline in ``example.py``; this module holds that logic
behind a clean callable API (:func:`run_showcase`) so ``example.py`` is a thin wrapper.

Behavior is identical to the prior inline script: each available engine renders a compact
still, an expanded still and a short ``expand`` transition video of ``testdata/airbl.scene.json``
at the 4K showcase size into ``outputs/<engine>/``; stills are gated as non-blank (``std > 20``);
the transition uses LINEAR easing so the clip animates uniformly (issue 329); and the sibling
``vexy-stax-js`` demos are rebuilt at the end (issue 330). Issue 335 §2 adds default held first/
last still frames to every transition video via :func:`vexy_stax.geometry.frame_plan`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image

from vexy_stax.engines import get_engine, is_available
from vexy_stax.scene import Scene, load_scene

# Color output formatting helpers (kept identical to the prior example.py output).
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

# Showcase defaults (unchanged from example.py): the airbl scene at the 4K showcase size,
# pygfx first and Blender last.
DEFAULT_SCENE = "testdata/airbl.scene.json"
DEFAULT_WIDTH = 1920 * 2
DEFAULT_HEIGHT = 1240 * 2
DEFAULT_ENGINES: tuple[str, ...] = ("pygfx", "playwright", "blender")
# Near-blank guard: the expanded layer-explosion on white legitimately reads ~23-24 std at 4K
# (issue 329); a blank/broken render is <10. 20.0 cleanly separates the two.
STD_GATE = 20.0


def std_of(path: Path) -> float:
    """Pixel-value standard deviation of an RGB image (near-blank guard)."""
    with Image.open(path) as im:
        return float(np.asarray(im.convert("RGB")).std())


def _scaled_scene(scene_path: str, width: int, height: int) -> Scene:
    """Load SCENE_PATH and rescale it to WIDTH×HEIGHT (gap + caption size scale with it)."""
    sc = load_scene(scene_path)
    scale = width / sc.size.width
    sc.size.width, sc.size.height = width, height
    sc.camera.gap *= scale
    if sc.caption_defaults and sc.caption_defaults.size is not None:
        sc.caption_defaults.size *= scale
    return sc


def rebuild_js_demos(here: Path) -> None:
    """Rebuild the sibling JS demos so scrollable.html + playable.html stay in sync (issue 330).

    Best-effort: runs ``vexy-stax-js/example.sh`` (which cleans outputs/ and regenerates the
    HTML demos, stills, video and scrollspy frames via headless Playwright). Skipped — never
    fatal — when the JS package, bash or its toolchain is unavailable, so the Python showcase
    still completes on machines without the JS stack.
    """
    js_dir = here.parent / "vexy-stax-js"
    script = js_dir / "example.sh"
    if not script.exists():
        print(f"{YELLOW}↔ skipping JS demo rebuild: {script} not found{NC}")
        return
    bash = shutil.which("bash")
    if bash is None or shutil.which("node") is None:
        print(f"{YELLOW}↔ skipping JS demo rebuild: bash/node unavailable{NC}")
        return
    print(f"\n{BLUE}=== rebuilding JS demos (scrollable.html + playable.html) ==={NC}")
    try:
        result = subprocess.run([bash, str(script)], cwd=js_dir, timeout=600)
        if result.returncode == 0:
            print(f"  {GREEN}✔ JS demos rebuilt in {js_dir / 'outputs'}{NC}")
        else:
            print(f"  {YELLOW}↔ JS demo rebuild exited {result.returncode} (non-fatal){NC}")
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"  {YELLOW}↔ JS demo rebuild skipped ({exc}){NC}")


def run_showcase(
    scene_path: str = DEFAULT_SCENE,
    engines: Sequence[str] = DEFAULT_ENGINES,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    *,
    rebuild_js: bool = True,
    project_dir: Path | None = None,
) -> bool:
    """Run the multi-engine showcase/benchmark; return True when everything passed.

    For each engine in ``engines`` (skipping unavailable ones, never fatal), render a compact
    still, an expanded still and a short ``expand`` transition video of ``scene_path`` at
    ``width``×``height`` into ``outputs/<engine>/``. Stills are gated as non-blank (``std >
    STD_GATE``). The transition uses LINEAR easing (issue 329). A benchmark file records each
    engine's wall time. When ``rebuild_js`` is set, the sibling JS demos are rebuilt at the end
    (issue 330). ``project_dir`` defaults to the vexy-stax-py package's repo root.
    """
    here = project_dir.resolve() if project_dir is not None else Path(__file__).resolve().parents[2]
    os.chdir(here)

    print(f"{BLUE}vexy-stax showcase — scene: {scene_path} @ {width}x{height}{NC}")

    bench_file = Path("outputs/benchmark.txt")
    bench_file.parent.mkdir(parents=True, exist_ok=True)
    with open(bench_file, "w") as f:
        f.write("Vexy Stax Rendering Benchmark\n")
        f.write("=============================\n")
        f.write(f"Resolution: {width}x{height}\n")
        f.write(f"Date: {time.ctime()}\n\n")
        f.write("Engine       | Duration (seconds)\n")
        f.write("-------------|-------------------\n")

    overall_ok = True
    summary: list[str] = []

    for engine_name in engines:
        print(f"\n{BLUE}=== engine: {engine_name} ==={NC}")

        if not is_available(engine_name):
            print(f"{YELLOW}↔ skipping {engine_name}: dependency unavailable{NC}")
            summary.append(f"{engine_name}: SKIPPED (unavailable)")
            with open(bench_file, "a") as f:
                f.write(f"{engine_name:<12} | SKIPPED\n")
            continue

        start_time = time.perf_counter()
        results: list[tuple[str, str, Path, str]] = []

        try:
            outdir = Path(f"outputs/{engine_name}")
            outdir.mkdir(parents=True, exist_ok=True)
            engine = get_engine(engine_name)

            # We want HIGH QUALITY rendering for the showcase (esp. Blender), so make sure the
            # turbo preview switch is off even if the caller's environment set it.
            if "VEXY_STAX_TURBO" in os.environ:
                os.environ.pop("VEXY_STAX_TURBO")

            # --- stills -----------------------------------------------------------------
            for view in ("compact", "expanded"):
                out = outdir / f"{view}.png"
                sc = _scaled_scene(scene_path, width, height)
                engine.render_image(sc, view, out)  # type: ignore[arg-type]

                if not out.exists() or out.stat().st_size == 0:
                    results.append((view, "FAIL", out, "(no file)"))
                    overall_ok = False
                    continue

                std = std_of(out)
                size = out.stat().st_size
                status = "PASS" if std > STD_GATE else "FAIL"
                results.append((view, status, out, f"bytes={size} std={std:.1f}"))
                if status == "FAIL":
                    overall_ok = False

            # --- short transition video -------------------------------------------------
            out = outdir / "transition.mp4"
            sc = _scaled_scene(scene_path, width, height)

            if sc.transition is None:
                results.append(("transition", "FAIL", out, "(scene has no transition)"))
                overall_ok = False
            else:
                sc.transition.kind = "expand"
                sc.transition.duration = 2.0
                sc.transition.wait = 0.0
                sc.transition.fps = 30
                # Issue 335 §3: video fps mirrors the transition fps so the (default 10-frame)
                # held first/last stills play back at the same rate as the morph.
                sc.video.fps = 30
                # Linear (not easeInOutCubic) so the showcase clip animates uniformly across its
                # full duration (issue 329).
                sc.transition.easing = "linear"

                engine.render_video(sc, out)

                if out.exists() and out.stat().st_size > 0:
                    size = out.stat().st_size
                    results.append(("transition", "PASS", out, f"bytes={size}"))
                else:
                    results.append(("transition", "FAIL", out, "(no file)"))
                    overall_ok = False

        except Exception as e:  # noqa: BLE001 — a broken engine must not abort the whole showcase
            print(f"{RED}✘ {engine_name} failed with exception: {e}{NC}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            overall_ok = False
            summary.append(f"{engine_name}: ERROR (exception)")
            with open(bench_file, "a") as f:
                f.write(f"{engine_name:<12} | ERROR\n")
            continue

        elapsed = time.perf_counter() - start_time
        with open(bench_file, "a") as f:
            f.write(f"{engine_name:<12} | {elapsed:.2f}s\n")
        print(f"  Benchmark: {engine_name} finished in {elapsed:.2f}s")

        for view, status, path, info in results:
            if status == "PASS":
                print(f"  {GREEN}✔ {view}{NC} {path} {info}")
                summary.append(f"{engine_name}/{view}: PASS {path} {info}")
            else:
                print(f"  {RED}✘ {view}{NC} {path} {info}")
                summary.append(f"{engine_name}/{view}: FAIL {path} {info}")

    # Keep the sibling JS demos (scrollable.html + playable.html) current (issue 330).
    if rebuild_js:
        rebuild_js_demos(here)

    print(f"\n{BLUE}===== summary ====={NC}")
    for s in summary:
        print(f"  {s}")

    if overall_ok:
        print(f"{GREEN}✅ Showcase complete.{NC}")
    else:
        print(f"{YELLOW}⚠ Showcase finished with some failures/skips (see summary).{NC}")
    return overall_ok
