---
this_file: issues/106-video-export-unimplemented.md
priority: MEDIUM
category: Features
created: 2025-11-06
---

# Issue 106: Video Export Stubbed and Untested

## Problem Statement

The `animate` CLI command and video export modules exist but **video encoding is completely stubbed**. Users expecting MP4/MOV output get TODO messages. Core project goal (issues/101.md) includes hero shot video export.

## Current State

### CLI Output (`src/vexy_stax/cli.py:102-108`)
```python
# Play animation and record
print(f"⏵ Playing animation (duration: {duration}s, hold: {hold}s)...")
browser.play_animation(duration=duration, hold_time=hold)

# TODO: Implement video recording
print("✓ Animation complete (recording not yet implemented)")
print(f"TODO: Save to {output}")
```

**User Experience**:
```bash
$ vexy-stax animate --images test.json --output hero.mp4
✓ Images loaded
⏵ Playing animation (duration: 1.5s, hold: 1.0s)...
✓ Animation complete (recording not yet implemented)
TODO: Save to hero.mp4
```

User: *"Wait, where's my video?"*

## Architecture Exists But Not Connected

### Export Module Has Video Support
`src/vexy_stax/renderer/export.py:83-124` implements:
- Frame collection from iterables
- Codec fallback chain (libx264 → h264 for MP4, prores_ks → prores for MOV)
- ImageIO v3 writer integration
- Error handling with diagnostics

### Camera Module Has Hero Animation
`src/vexy_stax/renderer/camera.py` implements:
- Spacing timeline with easing
- Frame-by-frame state generator
- Hero shot camera trajectory

### Missing Piece: Integration
No code connects:
1. Load scene → 2. Build timeline → 3. Render frames → 4. Encode video → 5. Save file

## Implementation Gap Analysis

### What Works
✅ Individual components tested with stubs
✅ `export_video()` function exists
✅ `build_spacing_timeline()` generates frame states
✅ Video writer interface defined

### What's Missing
❌ End-to-end video pipeline
❌ Real codec validation (never encoded actual video)
❌ MP4 vs MOV decision logic
❌ Frame rate configuration wiring
❌ Progress reporting for long renders
❌ Cleanup of temporary frames
❌ Video metadata (duration, dimensions, codec info)

## User Requirements from issues/101.md

> The app can export a @1, @2, @4 size MOV/MP4 of the hero shot animation that starts with the JSON scene, animates towards a flat full front view of the last slide (and then the distance between the slides is reduced to 0), then the camera moves back to the original position. The fps, length of the move, and length of the hold at the front view are all configurable.

### Expected CLI
```bash
vexy-stax animate \
  --images scene.json \
  --output hero.mp4 \
  --scale 2 \
  --fps 30 \
  --duration 2.0 \
  --hold 0.5 \
  --format mp4  # or mov
```

### Expected Output
```
Loading scene.json... ✓
Rendering animation (60 frames @ 30fps)...
  Frame 1/60 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  3%  0.8s remaining
  ...
  Frame 60/60 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  0.0s remaining
Encoding video (H.264)... ✓
✓ Exported hero.mp4 (3840x2160, 60 frames, 2.0s, 15.2 MB)
```

## Codec Support Matrix

| Format | Primary Codec | Fallback | Transparency | Quality | Compatibility |
|--------|---------------|----------|--------------|---------|---------------|
| MP4 | libx264 (H.264) | h264 | No | High | Universal |
| MOV | prores_ks (ProRes 4444) | prores | Yes | Very High | Pro tools |
| WebM | vp9 | vp8 | Yes | High | Web-first |

**Current implementation**: Only MP4/MOV planned
**Missing**: WebM support (lower priority)

## Technical Challenges

### 1. Codec Availability
- **Issue**: PyAV codecs depend on FFmpeg installation
- **H.264**: Usually available (patent-free in many regions)
- **ProRes**: May require additional FFmpeg builds
- **Detection**: Need to probe available codecs at runtime
- **Fallback**: Chain attempts, clear errors if all fail

### 2. Alpha Channel Handling
- **MP4 limitation**: H.264 doesn't support transparency (RGB only)
- **MOV advantage**: ProRes 4444 supports alpha (RGBA)
- **Solution**: Detect transparent scenes, recommend MOV, or composite over background

### 3. Memory Management
- **Problem**: Rendering all frames to memory before encoding
- **Risk**: 1000 frames @ 4K = multiple GB RAM
- **Solution**: Stream frames incrementally, don't accumulate list

### 4. Progress Reporting
- **User expectation**: See progress during long renders
- **Current**: No feedback for 30-60 second operations
- **Solution**: Rich progress bar with ETA

## Implementation Plan

### Phase 1: Basic MP4 Export (Week 1)
```python
# src/vexy_stax/video_pipeline.py

def render_video_pygfx(
    scene: SceneConfig,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
    duration: float,
    hold: float,
    scale: int = 1,
) -> VideoExportResult:
    """Render hero shot animation to video file."""

    # 1. Create renderer
    from .renderer import create_offscreen_bundle, OffscreenConfig
    bundle = create_offscreen_bundle(
        OffscreenConfig(size=(width * scale, height * scale))
    )

    # 2. Build scene
    from .renderer import build_scene, prepare_texture
    textures = [prepare_texture(img, deps) for img in scene.images]
    scene_graph = build_scene(scene, textures, deps)

    # 3. Build animation timeline
    from .renderer import build_spacing_timeline
    from .config import AnimationDefaults
    timeline = build_spacing_timeline(
        spacing=scene.params.z_spacing,
        defaults=AnimationDefaults(fps=fps, duration=duration, hold=hold)
    )

    # 4. Render frames (generator to save memory)
    def frame_generator():
        for frame_state in timeline.frames:
            # Update camera position
            camera = make_camera(scene, aspect_ratio=width/height)
            # Apply frame_state to camera
            # Render
            frame = bundle.renderer.render(scene_graph, camera)
            yield frame

    # 5. Export video
    from .renderer import export_video
    result = export_video(
        output_path=output_path,
        frames=frame_generator(),  # Stream frames
        fps=fps,
    )

    bundle.shutdown()
    return result
```

### Phase 2: MOV/ProRes Support (Week 1)
1. Test ProRes encoding availability
2. Add format detection from output path extension
3. Implement alpha channel preservation for MOV
4. Document when to use MP4 vs MOV

### Phase 3: Progress & Polish (Week 2)
```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeRemainingColumn

def render_video_with_progress(...) -> VideoExportResult:
    """Render video with rich progress bar."""

    total_frames = int(fps * duration) + int(fps * hold)

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeRemainingColumn(),
    ) as progress:

        render_task = progress.add_task(
            f"[cyan]Rendering animation ({total_frames} frames @ {fps}fps)",
            total=total_frames
        )

        def frame_generator_with_progress():
            for i, frame in enumerate(base_generator()):
                progress.update(render_task, advance=1)
                yield frame

        encode_task = progress.add_task(
            "[green]Encoding video...",
            total=None  # Indeterminate
        )

        result = export_video(
            frames=frame_generator_with_progress(),
            ...
        )

        progress.update(encode_task, completed=True)

    return result
```

### Phase 4: Testing & Validation (Week 2)
1. Smoke test that produces real MP4 file
2. Validate video plays in VLC/QuickTime/Browser
3. Verify frame count matches expected
4. Check duration is accurate
5. Validate video metadata
6. Test MOV with transparency

## CLI Integration Changes

### Update `cli.py:animate()`
```python
def animate(
    self,
    images: str,
    output: str = "animation.mp4",
    url: str = "http://localhost:5173/vexy-stax-js/",
    duration: float = 1.5,
    hold: float = 1.0,
    scale: int = 1,
    fps: int = 30,
    backend: str = "pygfx",  # New: choose backend
):
    """Animate and record video"""

    if backend == "pygfx":
        # New path
        from .loader import load_scene
        from .video_pipeline import render_video_pygfx

        scene = load_scene(images)
        result = render_video_pygfx(
            scene=scene,
            output_path=Path(output),
            width=scene.images[0].width,
            height=scene.images[0].height,
            fps=fps,
            duration=duration,
            hold=hold,
            scale=scale,
        )
        print(f"✓ Exported {output} ({result.frames} frames, {result.codec})")

    elif backend == "playwright":
        # Legacy path (TODO: implement Playwright recording)
        browser = VexyStaxBrowser(url=url, headless=True)
        # ... existing code ...
        print("✓ Animation complete (recording not yet implemented)")
```

## Success Criteria

1. ✅ `vexy-stax animate` produces playable MP4 file
2. ✅ Video contains correct number of frames
3. ✅ Video duration matches requested duration
4. ✅ MOV format works with transparency
5. ✅ Progress bar shows during render
6. ✅ Codec fallback works if primary unavailable
7. ✅ Tests validate real video encoding

## Known Limitations

### Expected Issues
- **Codec availability**: Users may need to install FFmpeg
- **Encode speed**: Real-time or slower depending on hardware
- **File size**: Uncompressed frames can be large
- **Platform differences**: Codec support varies by OS

### Documentation Needed
- FFmpeg installation per platform
- Codec troubleshooting
- Quality vs size tradeoffs
- When to use MP4 vs MOV

## Related Issues

- Issue 102: Architectural disconnect (video needs pygfx path)
- Issue 103: Smoke tests (video export needs validation)
- Issue 105: Quality validation (animation quality checking)
- Issue 104: GPU strategy (video rendering needs GPU)

## Priority Justification

**MEDIUM** (not HIGH) because:
- Core functionality (still images) is priority
- Video is enhancement, not MVP requirement
- Workaround: Export frames, encode externally
- But: Stated project goal includes video
- Value: High impact on user satisfaction once working
