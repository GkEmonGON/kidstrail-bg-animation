# KidsTrail / Animal BG Animation — Playbook

Future Claude: read this first when user asks for parallax / multi-layer Lottie BG animation.

## Goal pattern
Build layered Lottie BG for kids storybook app. Each variant (animal, bird, fish, ...) has two files:
- **back.json** = renders BEHIND character (sky/hills/trees/vines analogue per theme)
- **front.json** = renders IN FRONT of character (grass/big-leaves/flowers/particles analogue per theme)
- App stacks: `back` → `character` → `front` (Flutter Stack)
- Target: portrait 1080×1920 (9:16), seamless 8s loop @ 30fps, **≤300 KB per JSON (hard cap enforced in builder)**
- Front layer rule: NEVER include a layer that competes with the main character (e.g. fish-school removed from fish/front.json — would defocus child's eye from main fish)

## Preview rule — every variant gets 3 HTMLs
For variant `{variant}`, always create all three previews. Re-use the existing patterns:
- **preview-{variant}-back.html** — back.json only, white stage
- **preview-{variant}-front.html** — front.json only, checkered dark stage (shows transparency)
- **preview-{variant}.html** — stacked: back + character SVG placeholder + front, with aspect + layer toggles

Files for `animal` are unprefixed (legacy): `preview.html`, `preview-back.html`, `preview-front.html`. All new variants follow the `preview-{variant}-*.html` pattern.

## Project structure
```
KidsTrail/
├── CLAUDE.md                       ← this file
├── preview.html                    ← animal stacked preview (legacy, unprefixed)
├── preview-back.html               ← animal back-only
├── preview-front.html              ← animal front-only
├── preview-bird.html               ← bird stacked
├── preview-bird-front.html         ← bird front-only (bird has only bg.json + front concept)
├── preview-fish.html               ← fish stacked
├── preview-fish-back.html          ← fish back-only
├── preview-fish-front.html         ← fish front-only
├── scripts/
│   ├── gen_bubbles.py              ← procedural bubbles PNG generator (PIL)
│   └── build_fish_lottie.py        ← reusable Lottie builder w/ 300 KB hard guard
└── assets/
    ├── animal/  { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    ├── bird/    { bg.json, front-opt/ }
    └── fish/    { back.json, front.json, back/, front/, back-opt/, front-opt/ }
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

## LottieFiles Creator URLs (persistent — bookmark)
LottieFiles workspace: `cfaaeeca-95f3-4983-ae24-1b6eb132abc8`

**Animal project** (jungle theme, ID `ee6d09f7-f2a4-4832-9ae0-80bb222b4b3b`):
- Back file: https://creator.lottiefiles.com/?fileId=f0d87e92-6622-4fe9-a45a-2cd10059063a
- Front file: https://creator.lottiefiles.com/?fileId=b108fe9e-4abc-4c29-aff8-9c920c97967e

**Bird project** (sky theme, ID `13b438f8-cc3d-4556-aca0-648a0f4e6a74`):
- Single BG file: https://creator.lottiefiles.com/?fileId=646cec1d-06a6-4b74-804c-affdbf45ae47

MCP attaches to whichever Creator tab is **active**. Open ONE tab at a time for MCP work.

## Preview commands
```bash
# Start local server (project root)
python3 -m http.server 8765

# Animal (legacy unprefixed)
http://127.0.0.1:8765/preview.html              # stacked
http://127.0.0.1:8765/preview-back.html         # back only
http://127.0.0.1:8765/preview-front.html        # front only (checkered = transparent)

# Bird
http://127.0.0.1:8765/preview-bird.html         # stacked
http://127.0.0.1:8765/preview-bird-front.html   # front only

# Fish
http://127.0.0.1:8765/preview-fish.html         # stacked (clownfish placeholder)
http://127.0.0.1:8765/preview-fish-back.html    # back only
http://127.0.0.1:8765/preview-fish-front.html   # front only
```

## Builder script convention
Reusable Python Lottie builder lives in `scripts/build_{variant}_lottie.py` (e.g. `build_fish_lottie.py`). Pattern:
- `MAX_KB = 300` hard cap — raises `SystemExit` if any output JSON exceeds it
- Per-layer motion factories: `m_static`, `m_pan_y(amp)`, `m_pan_x(amp)`, `m_bob_y(amp)`, `m_bob_x(amp)`, `m_figure8(ax, ay)`, `m_breathe(pct)`, `m_pan_y_breathe(pan, pct)`
- Per-layer `y_offset` / `x_offset` override for repositioning (merge into motion dict: `{**m_bob_y(15), "y_offset": 380}`)
- Layer order in `BACK` / `FRONT` lists = front-to-back (index 0 = top)
- Embeds webps as data URIs — no external file deps at runtime

## Fish variant motion table (current)
| Layer | Slot | Motion |
|---|---|---|
| water-bg (opaque) | sky | breathe ±5% |
| distant-reef | hills | pan y -50 + breathe ±2% |
| kelp-forest | trees | pan y -70 + breathe ±3% |
| coral-cluster | vines | bob x ±10 |
| sand-floor | grass | pan y -8 |
| big-seaweed | big-leaves | bob y ±6 |
| bubbles-particles | particles | figure-8 ax=40 ay=60 |

Fish school (clownfish/angelfish/tang/puffer/seahorse/blue-tang) PNG kept on disk at `assets/fish/front/fish-school.png` but **NOT embedded in front.json** — would compete with app's main character fish. Toggle on by adding back to `FRONT` list in builder if needed for "underwater zoo" mode.
