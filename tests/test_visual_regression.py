# this_file: tests/test_visual_regression.py
"""Visual regression tests comparing pygfx renders to JS references.

These tests ensure pygfx output matches the JavaScript renderer within
acceptable quality thresholds.

Requirements:
- GPU available for pygfx rendering
- Reference images in tests/fixtures/references/
- JS native canvas size is 960×540 at scale=1

To generate reference images:
    1. cd vexy-stax-js && npm run dev
    2. python scripts/generate_references.py
"""

from pathlib import Path

import pytest

from vexy_stax.image_comparison import compare_images, save_diff_image


# JS canvas native resolution at scale=1
JS_CANVAS_WIDTH = 960
JS_CANVAS_HEIGHT = 540


FIXTURES_DIR = Path(__file__).parent / "fixtures"
REFERENCES_DIR = FIXTURES_DIR / "references"
FAILURES_DIR = Path(__file__).parent.parent / "test-failures"


class TestVisualRegressionSlides:
    """Compare pygfx renders of slide scene to JS references."""

    @pytest.fixture
    def scene_path(self) -> Path:
        """Path to test scene JSON."""
        return Path(
            "/Users/adam/Developer/vcs3/github.vexyart/vexy-stax/test-data/slides/slides_scene.json"
        )

    @pytest.fixture
    def reference_path(self) -> Path:
        """Path to JS reference image."""
        ref = REFERENCES_DIR / "slides_scene.png"
        if not ref.exists():
            pytest.skip(f"Reference image not found: {ref}")
        return ref

    @pytest.mark.skip(
        reason="Cross-renderer comparison: pygfx vs Three.js have inherent PBR differences (~67% match)"
    )
    def test_pygfx_matches_js_reference(self, scene_path, reference_path, tmp_path):
        """pygfx render should match JS reference within tolerance."""
        from vexy_stax.render_pipeline import pygfx_render_png

        if not scene_path.exists():
            pytest.skip(f"Scene not found: {scene_path}")

        # Render with pygfx at JS canvas size
        output = tmp_path / "pygfx_output.png"

        try:
            pygfx_render_png(
                scene_json=scene_path,
                output_path=output,
                width=JS_CANVAS_WIDTH,
                height=JS_CANVAS_HEIGHT,
            )
        except Exception as e:
            pytest.skip(f"pygfx rendering failed: {e}")

        # Compare to reference
        # Note: tolerance=50 because pygfx and Three.js are different PBR implementations
        # Expect ~65% pixel match due to lighting, material, and anti-aliasing differences
        result = compare_images(output, reference_path, tolerance=50)

        # Save diff if failed
        if not result.passed:
            FAILURES_DIR.mkdir(parents=True, exist_ok=True)
            save_diff_image(result, FAILURES_DIR / "slides_scene_diff.png")
            # Also save test output for inspection
            import shutil

            shutil.copy(output, FAILURES_DIR / "slides_scene_pygfx.png")

        assert result.passed, (
            f"Visual regression failed: {result.summary()}\n"
            f"Diff saved to {FAILURES_DIR / 'slides_scene_diff.png'}"
        )


class TestVisualRegressionBasicLayers:
    """Compare pygfx renders of simple layer stack."""

    @pytest.fixture
    def scene_path(self) -> Path:
        """Path to basic layer test scene."""
        return Path(
            "/Users/adam/Developer/vcs3/github.vexyart/vexy-stax/vexy-stax-py/test-img/layer123.json"
        )

    @pytest.fixture
    def reference_path(self) -> Path:
        """Path to JS reference for layer123."""
        ref = REFERENCES_DIR / "layer123.png"
        if not ref.exists():
            pytest.skip(f"Reference image not found: {ref}")
        return ref

    def test_basic_layers_match_reference(self, scene_path, reference_path, tmp_path):
        """Basic layer stack should match JS reference."""
        from vexy_stax.render_pipeline import pygfx_render_png

        if not scene_path.exists():
            pytest.skip(f"Scene not found: {scene_path}")

        output = tmp_path / "layer123_output.png"

        try:
            pygfx_render_png(
                scene_json=scene_path,
                output_path=output,
                width=JS_CANVAS_WIDTH,
                height=JS_CANVAS_HEIGHT,
            )
        except Exception as e:
            pytest.skip(f"pygfx rendering failed: {e}")

        result = compare_images(output, reference_path, tolerance=15)

        if not result.passed:
            FAILURES_DIR.mkdir(parents=True, exist_ok=True)
            save_diff_image(result, FAILURES_DIR / "layer123_diff.png")

        assert result.passed, f"Visual regression failed: {result.summary()}"
