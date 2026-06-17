#!/usr/bin/env bash
# this_file: example.sh
# Showcase: render compact still, expanded still, and a short transition video of
# testdata/airbl.scene.json with every available engine into outputs/<engine>/.
# Unavailable engines are skipped (not fatal). Stills are verified non-blank.
set -euo pipefail
cd "$(dirname "$0")"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCENE="testdata/airbl.scene.json"
WIDTH=960
HEIGHT=620
ENGINES=(blender pygfx playwright)

echo -e "${BLUE}vexy-stax showcase — scene: ${SCENE} @ ${WIDTH}x${HEIGHT}${NC}"

# Per-engine driver. Renders both stills + a short video, verifies stills are
# non-blank (PIL std > 30), and prints one "RESULT <kind> <PASS|FAIL> ..." line
# per artifact. Exits non-zero (caught by the caller) if the engine is missing.
run_engine() {
    local engine="$1"
    VEXY_ENGINE="$engine" VEXY_SCENE="$SCENE" VEXY_W="$WIDTH" VEXY_H="$HEIGHT" \
    VEXY_OUTDIR="outputs/$engine" VEXY_STAX_TURBO=1 \
    uv run python - <<'PY'
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from vexy_stax.engines import get_engine, is_available
from vexy_stax.scene import load_scene

engine_name = os.environ["VEXY_ENGINE"]
scene_path = os.environ["VEXY_SCENE"]
w = int(os.environ["VEXY_W"])
h = int(os.environ["VEXY_H"])
outdir = Path(os.environ["VEXY_OUTDIR"])
outdir.mkdir(parents=True, exist_ok=True)

if not is_available(engine_name):
    print(f"UNAVAILABLE {engine_name}: dependency not present", file=sys.stderr)
    sys.exit(3)

engine = get_engine(engine_name)


def std_of(path: Path) -> float:
    with Image.open(path) as im:
        return float(np.asarray(im.convert("RGB")).std())


# --- stills -----------------------------------------------------------------
for view in ("compact", "expanded"):
    out = outdir / f"{view}.png"
    sc = load_scene(scene_path)
    sc.size.width, sc.size.height = w, h
    engine.render_image(sc, view, out)
    if not out.exists() or out.stat().st_size == 0:
        print(f"RESULT {view} FAIL {out} (no file)")
        continue
    std = std_of(out)
    size = out.stat().st_size
    status = "PASS" if std > 30.0 else "FAIL"
    print(f"RESULT {view} {status} {out} bytes={size} std={std:.1f}")

# --- short transition video -------------------------------------------------
out = outdir / "transition.mp4"
sc = load_scene(scene_path)
sc.size.width, sc.size.height = w, h
if sc.transition is None:
    print(f"RESULT transition FAIL {out} (scene has no transition)")
else:
    # Keep it quick: single expand leg, ~1s, no hold, low fps.
    sc.transition.kind = "expand"
    sc.transition.duration = 1.0
    sc.transition.wait = 0.0
    sc.transition.fps = 15
    engine.render_video(sc, out)
    if out.exists() and out.stat().st_size > 0:
        size = out.stat().st_size
        print(f"RESULT transition PASS {out} bytes={size}")
    else:
        print(f"RESULT transition FAIL {out} (no file)")
PY
}

overall_ok=1
declare -a summary=()
log="$(mktemp "${TMPDIR:-/tmp}/vexy-example.XXXXXX")"
trap 'rm -f "$log"' EXIT

for engine in "${ENGINES[@]}"; do
    echo -e "\n${BLUE}=== engine: ${engine} ===${NC}"
    rc=0
    # stdout (RESULT lines) → log; stderr (engine chatter) → terminal.
    run_engine "$engine" >"$log" 2>&1 || rc=$?
    if [ "$rc" -eq 3 ]; then
        echo -e "${YELLOW}↔ skipping ${engine}: dependency unavailable${NC}"
        summary+=("${engine}: SKIPPED (unavailable)")
        continue
    fi
    if [ "$rc" -ne 0 ]; then
        echo -e "${RED}✘ ${engine} failed (rc=${rc}) — continuing with other engines${NC}"
        cat "$log"
        overall_ok=0
        summary+=("${engine}: ERROR (rc=${rc})")
        continue
    fi
    # Parse and report the RESULT lines from this engine's output.
    while IFS= read -r line; do
        case "$line" in
            "RESULT "*)
                read -r _ kind status path rest <<<"$line"
                if [ "$status" = "PASS" ]; then
                    echo -e "  ${GREEN}✔ ${kind}${NC} ${path} ${rest}"
                    summary+=("${engine}/${kind}: PASS ${path} ${rest}")
                else
                    echo -e "  ${RED}✘ ${kind}${NC} ${path} ${rest}"
                    overall_ok=0
                    summary+=("${engine}/${kind}: FAIL ${path} ${rest}")
                fi
                ;;
        esac
    done <"$log"
done

echo -e "\n${BLUE}===== summary =====${NC}"
for s in "${summary[@]}"; do
    echo "  $s"
done

if [ "$overall_ok" -eq 1 ]; then
    echo -e "${GREEN}✅ Showcase complete.${NC}"
else
    echo -e "${YELLOW}⚠ Showcase finished with some failures/skips (see summary).${NC}"
fi
