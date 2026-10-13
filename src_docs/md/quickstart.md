# Quick start

This walk-through takes a folder of layered PNGs to an expanded still, a compact still and a transition video. It uses the low-resolution sample deck that ships in the repository, `testdata/airbl-lores/`: nine PNGs, 1247 × 806 pixels, named `airbl-010-back.png` through `airbl-090-ui.png`.

## Prerequisites

- vexy-stax installed (see [Installation](installation.md)).
- For the video step: ffmpeg on `PATH`, and either Blender (the default video engine) or the pygfx engine.

## 1. Generate a scene file

```bash
vexy-stax dir2scene testdata/airbl-lores --out scene.json --transition_kind expand
```

`dir2scene` does the following:

1. Collects the `.png`, `.jpg`, `.jpeg` and `.webp` files in the folder.
2. Sorts them in natural order, so `2.png` comes before `10.png`. The first file becomes slide 0, the farthest plate.
3. Reads the first image's size and uses it as the scene size, here `1247 × 806`.
4. Sets the expanded plate spacing `camera.gap` to 38 % of the width, rounded down: `int(1247 × 0.38) = 473`.
5. Builds a caption from each file name. It strips the prefix shared by all names (`airbl-0`), strips leading and trailing digits and separators, replaces `-` and `_` with spaces, and title-cases the rest. `airbl-020-source.png` becomes `Source`; `airbl-090-ui.png` becomes `Ui`.
6. Because `--transition_kind expand` is set, adds a `transition` block (`duration` 3.0 s, `wait` 1.0 s, 30 fps, `easeInOutCubic`).
7. Writes the scene and prints its absolute path. Slide paths are written relative to the scene file.

!!! warning "Remove the explicit `gap: null` entries"
    `dir2scene` writes `"gap": null` into every slide. In the scene format an **explicit** `null` gap means "minimal gap", so every plate collapses to 3 points in the expanded view too. Delete the per-slide `gap` keys so the slides inherit `camera.gap`, for example with jq:

    ```bash
    jq 'del(.slides[].gap)' scene.json > scene.tmp && mv scene.tmp scene.json
    ```

## 2. Render the expanded view

```bash
vexy-stax render scene.json --view expanded --out beauty.png
```

With no `--engine`, stills use `pygfx`. The command prints `Wrote beauty.png (engine: pygfx)`. The camera is placed by an automatic framing solve: the deck is centred, and the margins on both sides equal the projected spacing between adjacent plates.

## 3. Render the compact view

```bash
vexy-stax render scene.json --view compact --out stack.png
```

The camera now looks straight down the `+Z` axis, the plates sit 3 points apart, and the frontmost plate fills the frame (`camera.distance` is `"100%"`). Captions with `show_in: "expanded"` (the `dir2scene` default) are hidden.

## 4. Render the transition video

```bash
vexy-stax video scene.json --out morph.mp4
```

With no `--engine`, video uses `blender`. For a faster preview use `--engine pygfx`.

The frame count comes from the scene. For this `expand` transition at 30 fps:

| Part | Frames |
|------|--------|
| Held first frame (`video.first_hold`) | 10 |
| Transition leg (`round(3.0 × 30)`) | 90 |
| Hold at the end of the leg (`round(1.0 × 30)`) | 30 |
| Held last frame (`video.last_hold`) | 10 |
| **Total** | **140** |

You can override the video settings without editing the scene:

```bash
vexy-stax video scene.json --engine pygfx --fps 24 --first_hold 0 --last_hold 0 --out morph.mp4
```

## 5. Make a flat preview

```bash
vexy-stax overlay scene.json --out flat.png
```

This composites the slides with Pillow, bottom-aligned and horizontally centred, without any 3D engine. It is a quick way to check that the layers line up.

## Next steps

- Adjust the camera, floor or captions: see the [Scene reference](scene-reference.md).
- Pick an engine for the job: see [Engines](engines.md).
- Script the same steps in Python: see [Python API](python-api.md).
