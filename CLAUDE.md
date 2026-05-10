# KidsTrail / Animal BG Animation — Playbook

Future Claude: read this first when user asks for parallax / multi-layer Lottie BG animation.

## Goal pattern
Build layered Lottie BG for kids storybook app. Two files:
- **back.json** = renders BEHIND animal (sky, hills, trees, vines)
- **front.json** = renders IN FRONT of animal (grass, big-leaves, flowers, particles)
- App stacks: `back` → `animal` → `front` (Flutter Stack)
- Target: portrait 1080×1920 (9:16), seamless 8s loop @ 30fps, **<300 KB per JSON**

## Project structure
```
KidsTrail/
├── CLAUDE.md                ← this file
├── preview.html             ← stacked preview (back + animal placeholder + front)
├── preview-back.html        ← back-only player
├── preview-front.html       ← front-only player
└── assets/animal/
    ├── back.json            ← Lottie (4 layers, embedded webps)
    ├── front.json           ← Lottie (4 layers, embedded webps)
    ├── back/                ← source PNGs (sky, hills, trees, vines)
    ├── front/               ← source PNGs (grass, big-leaves, flowers, particles)
    ├── back-opt/            ← webp optimized (for Creator import via jsDelivr URLs)
    └── front-opt/           ← webp optimized
```

## Layer roles (top → bottom = front → back in array)
| Layer | Role | Motion default |
|---|---|---|
| particles | top, sparkles + butterflies | figure-8 ax=40 ay=60 |
| flowers | accent color clusters | bob y ±15 |
| big-leaves | hanging vines from top OR leaf frame | bob y ±6 |
| grass | bottom band | pan -80 |
| vines | top corner leaves | bob x ±10 |
| trees | mid-lower silhouette | pan -70 + breathe ±3 |
| hills | distant mountains | pan -50 + breathe ±2 |
| sky | back, opaque gradient | breathe ±5 |

## Image asset workflow

### 1. Prompts (give user, they generate)
Each prompt MUST specify:
- Aspect `9:16 portrait 1080x1920`
- `TRANSPARENT BACKGROUND PNG with alpha channel` (except sky which is opaque)
- Layer position in canvas (top 30%, mid band, bottom 25%, etc)
- `simple flat watercolor shapes, limited palette` (compresses better)
- Explicit content + EXCLUSIONS (negative prompts)
- Edges plain — no critical detail near borders

VERIFY image content per file after generation — ChatGPT often mislabels (flowers came blank, grass came with trees in this project).

### 2. Optimize PNGs → webp
```bash
for f in assets/animal/back/*.png; do
  n=$(basename "$f" .png)
  cwebp -q 70 -resize 720 0 -alpha_q 75 -m 6 "$f" -o "assets/animal/back-opt/$n.webp"
done
```
**Settings cheat:** `q70 -resize 720` ≈ 30-80 KB per image. For ~300 KB total per Lottie JSON, use 720w q70. For tighter ~180 KB, use 600w q65.

### 3. Build Lottie JSON (Python)
Pattern (proven):
- Read image dim via PIL
- Compute scale + offset per image: `scale = max(1080/w, 1920/h) × 1.15 × 100`, `offset = -(w*s - 1080)/2, -(h*s - 1920)/2`
- Embed webp as data URI `data:image/webp;base64,...`
- Set asset `w/h` to **native image dim** (player upscales to canvas via scale)
- Keyframes: sine-sampled (smooth motion, no holds), LINEAR easing
- Densities: pan 17 kfs, bob 21 kfs, particle 33 kfs, breathe 17 kfs
- Layer order in array: top first, back last

See past commit `restructure assets, swap to portrait 1080x1920 with new images` for working code.

## Lottie Creator MCP gotchas

**Hard-learned:**
- **1 tab + 1 MCP server only.** Multiple stale `creator-mcp` procs cause `Another Creator MCP server already running`. Kill with `pkill -f creator-mcp` then user reopens 1 tab.
- **`scene.import` promise hangs** even though layer IS created. Don't `await` it. Use `creator.on("change:images", ...)` event-based polling OR fire-and-check-layer-count.
- **No `setTimeout` in sandbox.** Use event listeners or `globalThis._state` shared across script calls.
- **Image anchor is top-left** (NOT center). `position = (0,0)` puts image top-left at canvas origin. To center: `(-(displayW - canvasW)/2, -(displayH - canvasH)/2)`.
- **Rotation pivots at top-left** of image — small angles cause big swings at far corner. Prefer position bob over rotation for non-tilted motion.
- **Asset `uri` is readonly** — can't swap embedded data via MCP API. To change images: remove + reimport.
- **`scene.backgroundColor` is preview-only**, NOT exported. Lottie players default to transparent canvas. Front layer is automatically transparent.
- **Creator export embeds full-res PNGs** (~900 KB+). For optimal output, pre-encode to webp + import via URL (jsDelivr), NOT raw PNGs.
- **`scene.import` accepts HTTPS only.** No `http://`, `data:`, or local file paths. Use jsDelivr CDN: `https://cdn.jsdelivr.net/gh/{user}/{repo}@main/{path}`.
- **Multiple imports fire in parallel** — completion order non-deterministic. Identify by `asset.uri.length` matched against expected b64 size.
- **Browser-side cache** — user must hard-reload Creator (Cmd+Shift+R) after JSON change.
- **Save with Cmd+S in Creator** — reload loses scene state otherwise.

## Network / serving

- **Cloudflared quick tunnel often blocked** by ISP (port 7844 timeout). Don't rely on it.
- **GitHub + jsDelivr** is the most reliable image host: free, CORS-enabled, fast.
  - URL: `https://cdn.jsdelivr.net/gh/GkEmonGON/kidstrail-bg-animation@main/...`
  - Push first, wait ~10s for jsDelivr to cache, then Creator can import.

## Animation curve cheats
- LINEAR easing + dense sine-sampled keyframes = smooth perceived motion, no holds at endpoints.
- Cubic-bezier ease-in-out with few keyframes = looks like jumps. Avoid for short loops.
- Seamless loop: frame 0 value MUST equal frame `op` value.

## App integration (Flutter)
```yaml
# pubspec.yaml
dependencies:
  lottie: ^3.1.2
flutter:
  assets:
    - assets/animal/back.json
    - assets/animal/front.json
```
```dart
Stack(fit: StackFit.expand, children: [
  Lottie.asset('assets/animal/back.json',  fit: BoxFit.cover, repeat: true),
  YourAnimalWidget(),
  Lottie.asset('assets/animal/front.json', fit: BoxFit.cover, repeat: true),
])
```

## What NOT to do
- Don't build SEO/landing pages in this project (per global rules, use `teamz-lab-generic-landing-pages`).
- Don't write CLAUDE.md as wall of text — keep terse, scannable.
- Don't trust ChatGPT image generation content blindly — VERIFY by reading each file before mapping to layer names.
- Don't `await scene.import()` — it hangs. Poll layer count or use `change:images` event.
- Don't set rotation on layers that need to stay visually un-tilted — use position bob instead.
- Don't export from Creator UI for production — use the pre-built `assets/animal/*.json` (already optimized).
- Don't push to remote without confirming target with user — they previously meant `GkEmonGON/<repo>` not org.

## Repo
- GitHub: `https://github.com/GkEmonGON/kidstrail-bg-animation` (public, GkEmonGON)
- jsDelivr base: `https://cdn.jsdelivr.net/gh/GkEmonGON/kidstrail-bg-animation@main/`

## Preview commands
```bash
# Start local server (project root)
python3 -m http.server 8765
# Open in browser
http://127.0.0.1:8765/preview.html         # stacked
http://127.0.0.1:8765/preview-back.html    # back only
http://127.0.0.1:8765/preview-front.html   # front only (checkered = transparent)
```
