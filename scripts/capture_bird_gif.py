#!/usr/bin/env python3
"""
Capture the bird-v2 stacked preview (back + character + front) as a 90-frame
PNG sequence, then call ffmpeg to assemble into a GIF.

Requires:
- Local http server running on :8765 (python3 -m http.server 8765)
- ffmpeg installed
"""
from __future__ import annotations
import shutil, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "deliveries"
FRAMES_DIR = OUT / "_frames"
GIF_PATH = OUT / "bird-v2-preview.gif"

URL = "http://127.0.0.1:8765/preview-bird-v2.html"
TOTAL_FRAMES = 90
FPS = 30
STAGE_SELECTOR = "#stage"
VIEWPORT = {"width": 1400, "height": 1400}

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")

        # Wait until both lottie animations report DOMLoaded.
        # Note: preview HTML uses `const A` so A is not on window. Reference A directly.
        page.wait_for_function(
            "() => typeof A !== 'undefined' && A.back && A.front && "
            "A.back.totalFrames > 0 && A.front.totalFrames > 0",
            timeout=20000,
        )

        # Pause autoplay so we can step manually.
        page.evaluate("() => { A.back.pause(); A.front.pause(); }")

        # Step through all frames + screenshot stage element.
        stage = page.locator(STAGE_SELECTOR)
        # Ensure character is visible (placeholder monkey).
        page.evaluate("""() => {
            document.getElementById('tBack').checked = true;
            document.getElementById('tChar').checked = true;
            document.getElementById('tFront').checked = true;
        }""")

        for f in range(TOTAL_FRAMES):
            page.evaluate(
                f"() => {{ A.back.goToAndStop({f}, true); A.front.goToAndStop({f}, true); }}"
            )
            # Small wait for render
            page.wait_for_timeout(20)
            out_path = FRAMES_DIR / f"frame_{f:03d}.png"
            stage.screenshot(path=str(out_path))
            if f % 10 == 0:
                print(f"  frame {f:03d}/{TOTAL_FRAMES}", flush=True)

        browser.close()

    print(f"\nCaptured {TOTAL_FRAMES} frames to {FRAMES_DIR}")
    print("Building GIF via ffmpeg...")

    # First pass: build palette for clean colors
    palette = FRAMES_DIR / "palette.png"
    cmd_palette = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-vf", "scale=720:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette),
    ]
    subprocess.run(cmd_palette, check=True, capture_output=True)

    # Second pass: encode GIF using palette
    cmd_gif = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%03d.png"),
        "-i", str(palette),
        "-lavfi", "scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
        "-loop", "0",
        str(GIF_PATH),
    ]
    subprocess.run(cmd_gif, check=True, capture_output=True)

    size_mb = GIF_PATH.stat().st_size / (1024 * 1024)
    print(f"\nGIF ready: {GIF_PATH}  ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
