# Captions

A caption is a short text label for one slide. vexy-stax draws it as a small opaque **caption plate** with the text centred on it. Caption sizes, positions and opacities come from `vexy_stax.geometry`, so all engines place them the same way.

## Turning captions on and off

- Scene-wide: `"captions": false` removes every caption plate, and the slide plates stand directly on the floor. The default is `true`.
- Per slide: omit `caption`, or set `"show_in": "none"`.
- When generating a scene: `vexy-stax dir2scene assets --nocaptions`.

## Layout

With captions on, each slide forms a two-part stack at its own depth:

- the **caption plate** stands on the floor (its bottom edge on the floor line `Y = −height/2`), left-aligned with the slide plate;
- the **slide plate** is lifted by one caption-plate height, so it sits on top of the caption plate.

Both keep the slide's `Z` position, so in the angled expanded view each caption recedes with its slide.

## Size

All sizes derive from the caption size, 1 em in scene points:

| Quantity | Formula | 1920 × 1080 scene |
|----------|---------|-------------------|
| Caption size (`caption_size`) | `caption_defaults.size`, else `max(8, 0.10 × height)` | 108 |
| Plate height (`caption_plate_height`) | `caption size / 0.75` | 144 |
| Plate centre Y (`caption_plate_center_y`) | `−height/2 + plate height/2` | −468 |
| Text baseline Y (`caption_baseline_y`) | `−height/2 + 1.0 em` | −432 |
| Left edge X (`caption_anchor_x`) | `−width/2` | −960 |
| Plate width | text width + 0.75 em padding on each side | depends on the text |
| Slide lift (`slide_lift`) | plate height | 144 |

The text always takes 75 % of the plate height, whether the size is the default or set explicitly.

## Colours and border

| Element | Default | Set with |
|---------|---------|----------|
| Text | `#222222` | `caption_defaults.color`, or a caption's `style.color` |
| Plate fill | `edge.color` (`#f2f2f2`) | `caption_defaults.fill_color` |
| Plate border colour | `edge.color` | `caption_defaults.border_color` |
| Border thickness | `edge.width × height` (0, off) | `edge.width` |

The caption border uses the same thickness as the slide-plate border, so with the default `edge.width` of 0 neither has a border.

## Font

The default font is the bundled `vexy-stax.ttf` (Zalando Sans Expanded). vexy-stax-js matches it with the Google Font "Zalando Sans" at width 125 and weight 500.

To use another font, give a path to a font file:

```json
"caption_defaults": { "font": "/Library/Fonts/MyFont.ttf" }
```

A file path works in all engines. The Blender engine replaces anything that isn't an existing file with the bundled font. pygfx registers font files on the fly, maps `"vexy-stax"`, `"vexy stax"`, `"zalando sans"` and `"zalando sans expanded"` to the bundled font, and passes other family names to its font manager.

## Visibility per view

| `show_in` | Compact | Expanded | During a transition |
|-----------|---------|----------|---------------------|
| `expanded` (default) | 0 | 1 | Fades in near the expanded end, staggered |
| `compact` | 1 | 0 | `1 − t` |
| `both` | 1 | 1 | 1 |
| `none` | 0 | 0 | 0 |

## Fade timing

`caption_opacities(scene, t)` returns one opacity per slide at morph factor `t` (0 = compact, 1 = expanded). Engines call it for every frame. For an `expanded` caption on slide `i` of `N`:

```text
spread = stagger × window
start_i = (1 − window) + (i / (N − 1)) × spread
ramp    = window − spread
opacity = clamp((t − start_i) / ramp, 0, 1)
```

So the backmost caption starts first, at `t = 1 − window`, and the frontmost reaches full opacity exactly at `t = 1`. Captions are fully visible only in the expanded view.

With the defaults (`window` 0.9, `stagger` 0.3) and three slides, `spread` is 0.27 and `ramp` 0.63:

| `t` | Slide 0 | Slide 1 | Slide 2 |
|-----|---------|---------|---------|
| 0.1 | 0.000 | 0.000 | 0.000 |
| 0.5 | 0.635 | 0.421 | 0.206 |
| 0.75 | 1.000 | 0.817 | 0.603 |
| 0.9 | 1.000 | 1.000 | 0.841 |
| 1.0 | 1.000 | 1.000 | 1.000 |

### Stagger in frames

`caption_fade.stagger_frames` sets the step between consecutive captions in transition frames instead. It applies only when the scene has a transition. The step becomes `stagger_frames / leg_frames` of the morph, where `leg_frames = round(duration × transition.fps)`, and the total spread is capped at 95 % of the window so the frontmost caption still finishes at `t = 1`.

```json
"caption_fade": { "stagger_frames": 3 }
```

With `duration` 3.0 at 30 fps (90 frames per leg), each caption starts 3 frames (0.1 s) after the one behind it.

## Example

```json
{
  "version": 1,
  "caption_defaults": { "size": 108, "color": "#222222" },
  "caption_fade": { "window": 0.9, "stagger": 0.3 },
  "slides": [
    { "src": "layer-0-bg.png", "caption": { "text": "Background" } },
    {
      "src": "layer-1-content.png",
      "caption": { "text": "Content", "style": { "color": "#0066cc" } }
    },
    { "src": "layer-2-ui.png", "caption": { "text": "UI", "show_in": "both" } }
  ]
}
```
