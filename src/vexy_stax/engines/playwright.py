# this_file: src/vexy_stax/engines/playwright.py
"""Playwright engine — drives the built vexy-stax-js in headless Chromium (SPEC.md §5.3).

This engine renders by *reusing the JS package's three.js stage*: it serves the
repo over a localhost HTTP server (so three.js loads the airbl PNG textures and
the bundled ``dist/vexy-stax.element.js`` without ``file://`` CORS), mounts the
scene in a ``<vexy-stax>`` Web Component, and screenshots the WebGL canvas.

The scene is handed to the page as an inline ``config`` object (the same parser
path as ``loadScene``): each slide's resolved filesystem path is rewritten to an
``http://`` URL under the served root so the texture loader can fetch it.

View math is *not* duplicated here — the page's own ``stage`` consumes the shared
``geometry.js`` (verified numerically identical to ``geometry.py``), so the camera
pose matches the SPEC reference. For video this engine computes the per-frame
plan with the Python :mod:`vexy_stax.geometry` (``frame_plan``) and pushes each
frame state straight into ``stage.applyFrameState`` — the JS ``frameState`` shape
(``{camera:{position,target,fov,near}, gaps, opacities}``) maps 1:1 onto the
Python dataclasses, so the two paths stay in lockstep. Frames are assembled to an
mp4 with ffmpeg.

Stills are supersampled x2 (SSAA) and Lanczos-downscaled, matching the pygfx
engine's ``_SUPERSAMPLE`` so cross-engine output is comparable.
"""

from __future__ import annotations

import base64
import contextlib
import functools
import http.server
import shutil
import socketserver
import subprocess
import tempfile
import threading
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from PIL import Image

from vexy_stax import geometry as geo
from vexy_stax.engines.base import register
from vexy_stax.scene import Scene, Slide, View

# Repo root holds both the built JS (vexy-stax-js/dist) and the shared testdata.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DIST = _REPO_ROOT / "vexy-stax-js" / "dist" / "vexy-stax.element.js"
_JS_DIR = _REPO_ROOT / "vexy-stax-js"

# Supersample factor for stills: render NxN larger then Lanczos-downscale (SSAA).
# Matches the pygfx engine's _SUPERSAMPLE so the two engines' stills compare.
_SUPERSAMPLE = 2
# Time budget for the deck to mount + decode textures + first render.
_READY_TIMEOUT_MS = 60_000

# Synthetic harness route served by the in-process HTTP server (not a real file).
_HARNESS_ROUTE = "/__vexy_stax_harness__.html"

# The harness page: creates a <vexy-stax>, mounts the injected scene config at the
# SSAA size, and exposes hooks for setView / applyFrameState / canvas capture.
_HARNESS_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>vexy-stax playwright harness</title>
    <style>
      html, body {{ margin: 0; background: #fff; }}
      vexy-stax {{ display: block; }}
    </style>
  </head>
  <body>
    <script type="module" src="{dist_url}"></script>
    <script type="module">
      const STATUS = {{ phase: "init", error: null, ready: false }};
      window.__vexyStatus = () => STATUS;

      // Wait for the custom element to be defined by the bundled module.
      await customElements.whenDefined("vexy-stax");

      const W = {width};
      const H = {height};
      const SS = {ss};

      const el = document.createElement("vexy-stax");
      el.setAttribute("view", "{view}");
      el.style.width = W + "px";
      el.style.height = H + "px";
      // Inline scene object (overrides any `scene` URL); mirrors loadScene path.
      el.config = {config_json};

      el.addEventListener("error", (e) => {{
        STATUS.phase = "error";
        STATUS.error = String(e.detail?.error?.stack ?? e.detail?.error ?? e);
      }});
      el.addEventListener("ready", () => {{
        const stax = el.instance;
        window.__stax = stax;
        // SSAA: render the canvas at SS x the nominal size (pixelRatio 1 keeps the
        // WebGL context stable); Python Lanczos-downscales the screenshot. Aspect
        // is unchanged (W*SS / H*SS == W/H) so framing is identical.
        stax.stage.renderer.setPixelRatio(1);
        stax.stage.resize(W * SS, H * SS);
        stax.stage.render();
        STATUS.phase = "ready";
        STATUS.ready = true;

        window.__setView = async (view) => {{
          await stax.setView(view);
          stax.stage.render();
          return true;
        }};
        // Push a precomputed Python frame state into the JS stage (video path).
        window.__applyFrame = (state, t) => {{
          stax.stage.applyFrameState(state, t);
          stax.stage.render();
          return true;
        }};
        window.__canvasDataUrl = () => stax.stage.renderer.domElement.toDataURL("image/png");
        window.__canvasSize = () => {{
          const c = stax.stage.renderer.domElement;
          return {{ w: c.width, h: c.height }};
        }};
      }});

      document.body.appendChild(el);
    </script>
  </body>
</html>
"""


class _Harness:
    """Mutable holder so the harness HTML can be set after the port is known."""

    html: str = ""


class _RepoHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler rooted at the repo, plus one synthetic harness route.

    The harness body lives in a shared :class:`_Harness` instance (set on the
    handler subclass) so it can be filled in *after* the server starts and the
    bound port — needed to build the texture URLs — is known.
    """

    harness: _Harness = _Harness()

    def do_GET(self) -> None:  # noqa: N802 (stdlib casing)
        if self.path.split("?", 1)[0] == _HARNESS_ROUTE:
            body = self.harness.html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args: object) -> None:  # silence request logging
        pass


@contextlib.contextmanager
def _serve_repo():
    """Run a threaded HTTP server rooted at the repo.

    Yields ``(base_url, harness)``: write the rendered page into ``harness.html``
    once you've built it with the now-known ``base_url``.
    """
    harness = _Harness()
    handler = type("_HarnessHandler", (_RepoHandler,), {"harness": harness})
    factory = functools.partial(handler, directory=str(_REPO_ROOT))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), factory)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        yield f"http://127.0.0.1:{port}", harness
    finally:
        httpd.shutdown()
        httpd.server_close()


def _rel_to_root(path: str) -> str:
    """Return ``path`` relative to the repo root with forward slashes."""
    return Path(path).resolve().relative_to(_REPO_ROOT).as_posix()


def _slide_src_url(slide: Slide, base_url: str) -> str:
    """Map a slide's resolved filesystem ``src`` to a served HTTP URL.

    ``data:`` URIs pass through untouched. Filesystem paths must live under the
    repo root (the served root) so the page's texture loader can fetch them.
    """
    src = slide.src
    if src.startswith("data:"):
        return src
    try:
        rel = _rel_to_root(src)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"slide src {src!r} is outside the served repo root {_REPO_ROOT}; "
            "the playwright engine serves textures from the repo and cannot reach it"
        ) from exc
    return f"{base_url}/{rel}"


def _scene_config(scene: Scene, base_url: str) -> dict:
    """Serialize ``scene`` to the JS ``config`` object with HTTP texture URLs.

    Drops ``None`` fields so the strict JS parser (``parseScene``) accepts it, and
    rewrites every slide ``src`` to a served URL.
    """
    config = scene.model_dump(by_alias=False, exclude_none=True)
    config.pop("schema_ref", None)
    config.pop("$schema", None)
    for slide_cfg, slide in zip(config["slides"], scene.slides, strict=True):
        slide_cfg["src"] = _slide_src_url(slide, base_url)
    return config


def _frame_state_dict(state: geo.FrameState) -> dict:
    """Convert a Python FrameState to the JS ``frameState`` plain-object shape."""
    return asdict(state)


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise an actionable error."""
    found = shutil.which("ffmpeg")
    if not found:
        raise FileNotFoundError("ffmpeg not found on PATH. Install with: brew install ffmpeg")
    return found


def _require_dist() -> None:
    """Ensure the built JS bundle exists, with an actionable hint if not."""
    if not _DIST.exists():
        raise FileNotFoundError(
            f"built JS bundle not found at {_DIST}. Build it first:\n  (cd {_JS_DIR} && npm install && npm run build)"
        )


class _Browser:
    """A mounted harness page in headless Chromium; reused across frames.

    Built once per render: starts the HTTP server, launches Chromium, mounts the
    scene at the SSAA size, and waits for the deck to be ready. ``set_view`` and
    ``apply_frame`` drive the existing stage; ``capture`` reads the canvas.
    """

    def __init__(self, scene: Scene, view: View) -> None:
        import json as _json

        from playwright.sync_api import sync_playwright

        _require_dist()
        self._scene = scene
        self._exit = contextlib.ExitStack()
        base_url, harness = self._exit.enter_context(_serve_repo())

        # Build the harness now that the port (hence texture URLs) is known.
        config = _scene_config(scene, base_url)
        harness.html = _HARNESS_HTML.format(
            dist_url=f"{base_url}/vexy-stax-js/dist/vexy-stax.element.js",
            width=scene.size.width,
            height=scene.size.height,
            ss=_SUPERSAMPLE,
            view=view,
            config_json=_json.dumps(config),
        )

        self._pw = self._exit.enter_context(sync_playwright())
        self._browser = self._pw.chromium.launch(headless=True)
        self._exit.callback(self._browser.close)
        self._page = self._browser.new_page(
            viewport={"width": scene.size.width, "height": scene.size.height},
            device_scale_factor=1,
        )

        errors: list[str] = []
        self._page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        self._page.on("pageerror", lambda e: errors.append(str(e)))

        self._page.goto(f"{base_url}{_HARNESS_ROUTE}", wait_until="load")
        self._page.wait_for_function(
            "() => { const s = window.__vexyStatus && window.__vexyStatus();"
            " return s && (s.ready || s.phase === 'error'); }",
            timeout=_READY_TIMEOUT_MS,
        )
        status = self._page.evaluate("() => window.__vexyStatus()")
        if status.get("phase") == "error":
            self._exit.close()
            raise RuntimeError(
                f"vexy-stax-js harness failed to mount: {status.get('error')}\n"
                + ("console errors:\n" + "\n".join(errors) if errors else "")
            )

    def set_view(self, view: View) -> None:
        self._page.evaluate("(v) => window.__setView(v)", view)

    def apply_frame(self, state: geo.FrameState, t: float) -> None:
        self._page.evaluate(
            "(args) => window.__applyFrame(args[0], args[1])",
            [_frame_state_dict(state), t],
        )

    def capture(self) -> Image.Image:
        """Return the current canvas as a Pillow RGBA image, Lanczos-downscaled."""
        data_url = self._page.evaluate("() => window.__canvasDataUrl()")
        raw = base64.b64decode(data_url.split(",", 1)[1])
        im = Image.open(BytesIO(raw)).convert("RGBA")
        target = (self._scene.size.width, self._scene.size.height)
        if im.size != target:
            im = im.resize(target, Image.LANCZOS)
        return im

    def close(self) -> None:
        self._exit.close()


class PlaywrightEngine:
    """Headless-browser renderer driving vexy-stax-js (SPEC.md §5.3)."""

    name = "playwright"

    def render_image(self, scene: Scene, view: View, out: Path) -> None:
        """Render a single still of SCENE in VIEW (compact|expanded) to a PNG."""
        browser = _Browser(scene, view)
        try:
            browser.set_view(view)
            im = browser.capture()
        finally:
            browser.close()
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "PNG")

    def render_video(self, scene: Scene, out: Path) -> None:
        """Render SCENE's transition to an mp4 (requires ``scene.transition``)."""
        if scene.transition is None:
            raise ValueError("scene has no transition; nothing to animate (use render_image)")
        _require_ffmpeg()
        plan = geo.frame_plan(scene)
        factors = _morph_factors(scene)
        if not plan:
            raise ValueError("transition produced no frames")

        # Mount once; the deck's initial view is irrelevant since every frame is
        # driven explicitly via applyFrameState.
        browser = _Browser(scene, "compact")
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="vexy_stax_pw_") as tmp:
                tmp_dir = Path(tmp)
                for i, (state, t) in enumerate(zip(plan, factors, strict=True)):
                    browser.apply_frame(state, t)
                    im = browser.capture()
                    im.convert("RGB").save(tmp_dir / f"frame_{i:05d}.png", "PNG")
                _encode_video(tmp_dir, scene.transition.fps, out)
        finally:
            browser.close()
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg finished but {out} is missing/empty")


def _morph_factors(scene: Scene) -> list[float]:
    """Per-frame morph factor (0=compact, 1=expanded), matching ``frame_plan``.

    Mirrors ``geometry.frame_plan``'s leg/hold layout so caption fades stay in
    lockstep with the camera/opacity morph it produced (same logic as pygfx).
    """
    tr = scene.transition
    assert tr is not None
    leg_frames = round(tr.duration * tr.fps)
    wait_frames = round(tr.wait * tr.fps)
    legs = geo._LEGS[tr.kind]
    factors: list[float] = []
    for start, end in legs:
        for i in range(leg_frames):
            p = i / leg_frames if leg_frames else 0.0
            eased = geo.ease(tr.easing, p)
            factors.append(start + (end - start) * eased)
        factors.extend(end for _ in range(wait_frames))
    return factors


def _encode_video(frame_dir: Path, fps: int, out: Path) -> None:
    """Assemble a PNG sequence into an H.264 mp4 with ffmpeg."""
    ffmpeg = _require_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frame_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr[-2000:] if result.stderr else result.stdout[-2000:]
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{tail}")


register(PlaywrightEngine())
