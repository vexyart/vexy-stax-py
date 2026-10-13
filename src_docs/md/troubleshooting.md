# Troubleshooting

## Expanded view looks collapsed

**Symptom.** A scene made with `dir2scene` renders the expanded view with all plates pressed together.

**Cause.** `dir2scene` writes `"gap": null` into every slide. An explicit `null` (or `0`) per-slide gap means "minimal gap" (`MIN_GAP`, 3 points). Only an omitted key inherits `camera.gap`.

**Fix.** Remove the per-slide `gap` keys:

```bash
jq 'del(.slides[].gap)' scene.json > scene.tmp && mv scene.tmp scene.json
```

When you write scenes from Python, save with `model_dump_json(by_alias=True, exclude_none=True)`.

## `--captions false` still generates captions

Fire reads lowercase `false` as a string, and any non-empty string counts as true. Use `--nocaptions` or `--captions=False`. The same applies to `--reverse` and `--juicy`.

## `Unknown engine 'NAME'`

The `--engine` value must be `pygfx`, `blender` or `playwright`. The message lists the registered names. Nothing is written.

## `scene has no transition; nothing to animate`

`vexy-stax video` needs a `transition` block. Add one to the scene, or regenerate it with `dir2scene --transition_kind expand` (or `collapse`, `expand_collapse`, `collapse_expand`).

## `ffmpeg not found on PATH`

All three engines assemble video with ffmpeg. Install it (`brew install ffmpeg`, `sudo apt install ffmpeg`) and make sure it is on `PATH`. Stills don't need it.

## `Blender not found`

The Blender engine looks for `blender` on `PATH`, then `/opt/homebrew/bin/blender`, then `/Applications/Blender.app/Contents/MacOS/Blender`. Install Blender (`brew install --cask blender` on macOS) or add its binary to `PATH`.

`vexy-stax engines` lists Blender only when it is on `PATH`, even if one of the fallback locations works.

## `built JS bundle not found`

The Playwright engine needs `vexy-stax-js/dist/vexy-stax.element.js` in a `vexy-stax-js` checkout next to `vexy-stax-py`. Build it:

```bash
cd ../vexy-stax-js && npm install && npm run build
```

If Chromium is missing, install it with `python -m playwright install chromium`.

## Blender renders are slow

Cycles renders every frame of a transition, and the compact view sends rays through the whole transparent stack. Options:

- Set `VEXY_STAX_TURBO=1` to render with Eevee and 8 samples.
- Render previews with `--engine pygfx`.
- Lower the frame count: `vexy-stax video scene.json --fps 24 --frames 48`.

Blender video is already capped at 1920 pixels on the long edge.

## A video is longer than `duration` suggests

Videos include held frames: `first_hold` and `last_hold` (10 each by default) plus `round(wait × fps)` frames after every leg. Set `--first_hold 0 --last_hold 0`, or `"wait": 0` in the transition, for a clip with no holds.

## Captions are missing from the compact view

That is the default: `show_in: "expanded"` captions are invisible in the compact view and fade in during the expand. Use `"show_in": "both"` for a caption that is always visible.

## The scene fails to load

`load_scene()` raises `pydantic.ValidationError` with the path of the bad field. Common causes:

- a misspelled or unknown field (every model forbids extra fields),
- `version` other than `1`,
- an empty `slides` array,
- a value out of range, such as `fov` of 180 or a negative `gap`.

An image that doesn't exist fails later, when an engine or `overlay` reads it, with `FileNotFoundError: Image not found: PATH`.
