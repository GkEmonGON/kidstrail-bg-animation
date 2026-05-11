#!/usr/bin/env python3
"""
Generate animal-v2 BG elements via OpenRouter (google/gemini-2.5-flash-image).
Saves PNGs to assets/animal-v2/raw/. Skips elements already present (resume-friendly).
Reads OPENROUTER_API_KEY from .env in repo root.

Cost: ~$0.038/image. Full batch (10 elements) ≈ $0.40.
"""
from __future__ import annotations
import base64, json, os, sys, time
from pathlib import Path
from urllib import request as urlreq, error as urlerr

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "animal-v2" / "raw"
ENV_FILE = ROOT / ".env"

MODEL = "google/gemini-2.5-flash-image"
URL = "https://openrouter.ai/api/v1/chat/completions"

STYLE_SUFFIX = (
    "flat vector illustration, hard clean edges, 3-4 solid colors only, "
    "NO gradients NO shading NO texture NO noise, thick black outline 3px, "
    "cartoon style for kids ages 3-6, transparent PNG background with alpha channel, "
    "1:1 square aspect ratio 1024x1024, isolated single element on transparent, "
    "no shadow, no ground, no scene context"
)

ELEMENTS: list[dict] = [
    # ----- BACK SIDE -----
    {
        "name": "back-base",
        "side": "back",
        "prompt": (
            "Full jungle scene background, square composition 1080x1080, "
            "warm pastel sky upper third, soft rolling green hills middle, "
            "ground layer bottom with hint of grass and roots, "
            "distant tropical canopy silhouettes left and right edges, "
            "centered empty middle area where a character will stand, "
            "PALETTE: sky #FFE0B2, hills #66BB6A, mid-green #43A047, "
            "deep-jungle #1B5E20, warm-ground #8D6E63, "
            "flat vector illustration, hard clean edges, NO gradients NO shading NO texture, "
            "thick black outline 3px, cartoon style for kids ages 3-6, "
            "1:1 square 1080x1080, opaque background (NOT transparent), no characters no animals no people"
        ),
    },
    {
        "name": "back-tree-left",
        "side": "back",
        "prompt": (
            "Single tall jungle tree silhouette with leafy canopy, trunk brown, leaves bright green, "
            "PALETTE: trunk #6D4C41, canopy-light #66BB6A, canopy-dark #2E7D32, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "back-tree-right",
        "side": "back",
        "prompt": (
            "Single tropical palm tree variant, curved trunk, fanned palm leaves at top, "
            "PALETTE: trunk #795548, fronds-light #81C784, fronds-dark #388E3C, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "back-vine-left",
        "side": "back",
        "prompt": (
            "Hanging vine with heart-shaped leaves trailing down from top, decorative jungle vine, "
            "PALETTE: stem #4E342E, leaf-light #9CCC65, leaf-dark #558B2F, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "back-vine-right",
        "side": "back",
        "prompt": (
            "Hanging vine with oval leaves and tiny pink flowers, decorative jungle vine, "
            "PALETTE: stem #4E342E, leaf #689F38, flower-pink #F48FB1, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "back-bush",
        "side": "back",
        "prompt": (
            "Single round leafy jungle bush, low to ground, layered leafy shapes, "
            "PALETTE: leaf-light #7CB342, leaf-mid #558B2F, leaf-dark #33691E, " + STYLE_SUFFIX
        ),
    },
    # ----- FRONT SIDE -----
    {
        "name": "front-big-leaf",
        "side": "front",
        "prompt": (
            "Single large tropical monstera leaf with hole patterns, foreground prop, "
            "PALETTE: leaf-light #66BB6A, leaf-mid #388E3C, leaf-dark #1B5E20, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "front-grass-tuft",
        "side": "front",
        "prompt": (
            "Single tall jungle grass tuft cluster, blades pointing up, "
            "PALETTE: grass-light #AED581, grass-mid #7CB342, grass-dark #33691E, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "front-butterfly",
        "side": "front",
        "prompt": (
            "Single colorful cartoon butterfly side view, two large wings, antennae, "
            "PALETTE: wing-pink #F06292, wing-orange #FFB74D, body-black #212121, " + STYLE_SUFFIX
        ),
    },
    {
        "name": "front-firefly",
        "side": "front",
        "prompt": (
            "Single tiny glowing firefly with bright yellow body and soft glow halo, "
            "PALETTE: glow-yellow #FFEB3B, body #FBC02D, wing-light #FFF59D, " + STYLE_SUFFIX
        ),
    },
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call_api(api_key: str, prompt: str) -> tuple[bytes, float]:
    body = json.dumps({
        "model": MODEL,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urlreq.Request(
        URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/GkEmonGON/kidstrail-bg-animation",
            "X-Title": "KidsTrail BG generator",
        },
        method="POST",
    )
    with urlreq.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data and data["error"]:
        raise RuntimeError(f"API error: {data['error']}")
    msg = data["choices"][0]["message"]
    imgs = msg.get("images") or []
    if not imgs:
        raise RuntimeError(f"No image in response. text={msg.get('content')!r}")
    img_url = imgs[0]["image_url"]["url"]
    if not img_url.startswith("data:"):
        raise RuntimeError(f"Unexpected image url format: {img_url[:60]}")
    b64 = img_url.split(",", 1)[1]
    cost = float(data.get("usage", {}).get("cost", 0.0))
    return base64.b64decode(b64), cost


def main() -> int:
    env = load_env(ENV_FILE)
    api_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in .env or environment", file=sys.stderr)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_cost = 0.0
    n_done = n_skip = n_fail = 0
    for el in ELEMENTS:
        out_path = OUT_DIR / f"{el['name']}.png"
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"[skip] {el['name']} (already exists)")
            n_skip += 1
            continue
        print(f"[gen ] {el['name']} ({el['side']}) ...", flush=True)
        try:
            png, cost = call_api(api_key, el["prompt"])
            out_path.write_bytes(png)
            total_cost += cost
            n_done += 1
            print(f"        -> {out_path.name}  {len(png)//1024} KB  ${cost:.4f}")
            time.sleep(0.5)
        except (urlerr.URLError, RuntimeError) as e:
            print(f"        FAIL: {e}", file=sys.stderr)
            n_fail += 1
    print(f"\nDone. generated={n_done} skipped={n_skip} failed={n_fail} total_cost=${total_cost:.4f}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
