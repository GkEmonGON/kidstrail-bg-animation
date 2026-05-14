# KidsTrail / Animal BG Animation — Playbook

Future Claude: read this first when user asks for parallax / multi-layer Lottie BG animation.

**⚠️ MANDATORY before new variant:** Read `~/.claude/projects/-Users-.../memory/build_lessons.md` — contains every bug I hit in animal-v2 (May 2026) with root cause + fix. User explicitly demanded these be saved so they're not repeated. Top issues: breathe-sin-negative exposing white bg, AI checker-pattern fake transparency, content-bbox anchors, tree-root bush placement, opacity-flicker on pop-drift.

**⚠️ CLIENT PREFERENCES (Teamz Lab Animation chat, review 2026-05-13)** — apply to ALL future variants:
- **Character = main focus**: 80-84% of stage width, top:62-65%, bob-translate only (no rotate)
- **Depth-pair living decor**: 3 butterflies/birds in BACK + 3 in FRONT (smaller in back for parallax)
- **Paw-cover foreground bush** (w=480-500) at canvas bottom overlapping char's feet → "lion er pa ta bush e ekto dhaka pore thakbe" pattern
- **Both bottom corners need a 3-piece stack**: bush + flower + grass each side
- **Client provides character PNG** (Gemini-generated) — bg-key it before use (66.7% bg in lion test)
- **Client speaks Banglish** — `ta`=counter, `boosh`=bush, `pa`=leg, `dile valo hoy`=would be good if placed, `tik ase`=fine, `proceed koro`=move ahead. Glossary in build_lessons.md.

---

## ⭐ NEW TARGET PATTERN (client reference, 2026-05-12) — USE THIS GOING FORWARD

Client gave reference file `80692370-1321-46b2-8674-7e2ea36f93ad` (Lottie Creator). All future variants follow this style. Old raster-band approach below is LEGACY — keep working files, but new builds use this pattern.

### Canvas
- **Square 1080×1080** (NOT portrait, NOT landscape). Same scene drives phone + tablet + web equally.
- 30fps, **3s loop = 90 frames** (NOT 8s — denser motion feel).
- Seamless loop: frame 0 transform == frame 90 transform.

### Source art = VECTOR, not raster
- ZERO image layers. All shapes are vector shape layers (paths/groups/fills).
- Client provides SVG (or built directly in Creator via shapes). NEVER bake into PNG bands.
- Each visual element = its own shape layer. Reference file has 33 layers — many small pieces, not few big bands.

### Layer architecture (top → bottom of `scene.layers` array)
| Group | Count guide | Motion type | Role |
|---|---|---|---|
| Floating accents (name `b`) | ~5–10 | position 3kf + scale 2kf + opacity 2kf | pop-in + drift (butterflies, sparkles, birds, balloons, falling petals) |
| Mid-front decor (name `1`) | ~5–10 | rotation 3kf only, ≤2.5° | wiggle in place (flowers, leaves, small props) |
| Mid-back decor (name `2`) | ~3–8 | rotation 3kf only, ≤2.5° | wiggle in place (grass tufts, bushes) |
| Edge chain (name `1`–`9`) | ~5–10 | rotation 3kf only, ≤2.5° | vertical/horizontal chain (petals on stem, vines on edge) |
| **Base illustration** (name `b`, LAST in array) | exactly 1 | NO keyframes — static | scene-centered anchor drawing |

Layer names = SHORT codes (`b`, `1`, `2`, numbered), NOT semantic ("tree","grass"). Codes mark z-role + motion class.

### Back/front split (the sandwich)
- Artist build ONE big scene with all pieces.
- Mark each piece "behind character" OR "in front of character".
- Export TWO files:
  - `back.json` = base illustration + everything tagged BEHIND
  - `front.json` = everything tagged IN FRONT (transparent canvas)
- App stack (Flutter `Stack`): `back.json` → character widget → `front.json`. Character look like he stand inside scene. Same scene reusable for any character (kid, fruit, vehicle, fish).
- Front rule still applies: nothing in `front.json` should compete with main character's silhouette.

### Motion library (only 2 motion types)
1. **Pop-drift** (floating accents only):
   - opacity: 0 → 100 → 100 (fade in over ~10 frames, hold)
   - scale: 80% → 105% → 100% (overshoot pop)
   - position: 3 keyframes describing soft curve drift, return to start at frame 90
2. **Rotation wiggle** (everything else):
   - rotation: 0 → ±1.5° → 0 (3 keyframes, sine-feel, pivot at layer's own center)
   - NO translation. NO scale change. Pure rotation.
   - Stagger phase per layer (offset start by 5–15 frames) so wiggles don't sync.

LINEAR easing, dense kfs > cubic easing, sparse kfs. Same rule as before.

### Builder workflow — what shipped in animal-v2 (raster-bridge approach, $0.59 total)
1. Generate elements via OpenRouter `google/gemini-2.5-flash-image` (flux-schnell NOT available on OR). ~$0.038/image.
2. **bg-key pipeline** (4 steps, see `build_lessons.md`): flood-fill from corners → interior pure-white kill → zero RGB in transparent → cwebp with `-alpha_cleanup`.
3. Compress to webp (q75, 1024 max).
4. Run `scripts/build_animal_v2_lottie.py` (template for new variants). Key elements:
   - Content-bbox-aware anchors (NOT image-bbox — AI images have 30%+ padding)
   - `(1+sin)/2` based m_breathe (NEVER negative)
   - Asset dedup map (one webp → many layer instances)
   - Shadow shape-layers under ground elements
   - Baked rot_offset for un-aligned scatter look
5. Generate 3 previews same as legacy rule.

**For new variants, COPY `build_animal_v2_lottie.py` as template + adjust LAYERS_BACK + LAYERS_FRONT only.**

### Why this is better than legacy raster bands
- Reusable: one scene → many characters sit in middle slot.
- Smaller files: vector >> embedded webp data URIs.
- Sharper at every screen size (no upscale blur).
- Each piece animates alone → richer feel without bigger file.
- Easier client revisions: change one shape, not re-export whole PNG band.

---

## LEGACY: Raster-band approach (current variants — keep for reference)

Variants below (animal, bird, fish, flower, fruit, vegetable, transport) were built with raster-band approach. Keep their files working. New variants use the vector pattern above.

## Goal pattern (LEGACY)
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
├── preview-vegetable.html           ← vegetable stacked (farm/garden theme)
├── preview-vegetable-back.html      ← vegetable back-only
├── preview-vegetable-front.html     ← vegetable front-only
├── preview-transport.html           ← transport stacked (road/vehicle theme)
├── preview-transport-back.html      ← transport back-only
├── preview-transport-front.html     ← transport front-only
├── scripts/
│   ├── gen_bubbles.py              ← procedural bubbles PNG generator (PIL)
│   ├── build_fish_lottie.py        ← reusable Lottie builder w/ 300 KB hard guard
│   ├── build_flower_lottie.py
│   ├── build_fruit_lottie.py
│   ├── build_vegetable_lottie.py
│   └── build_transport_lottie.py
└── assets/
    ├── animal/    { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    ├── bird/      { bg.json, front-opt/ }
    ├── fish/      { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    ├── flower/    { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    ├── fruit/     { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    ├── vegetable/ { back.json, front.json, back/, front/, back-opt/, front-opt/ }
    └── transport/ { back.json, front.json, back/, front/, back-opt/, front-opt/ }
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
- **Image anchor differs by environment:**
  - **In Creator UI**: imports default to **CENTER anchor**. Layer's `anchor` property is NOT exposed in the MCP API surface (not on `layer.*` keys). Position math = `(sceneW/2, sceneH/2)` for cover-fit, NOT top-left offset. Confirmed in fruit-bg session 2026-05-11 — using `(-196, -144)` left image rendering far off-canvas; switching to `(540, 960)` for 1080×1920 scene fixed it.
  - **In hand-built Lottie JSON via Python builder**: anchor `[0,0,0]` (top-left). Position uses `-(displayW-canvasW)/2, -(displayH-canvasH)/2`. Lottie players honor this.
  - **Net rule**: when authoring via MCP, use scene-center coords. When writing JSON directly, use top-left math. Do NOT cross-pollinate.
- **`scene.import` PREPENDS new layer to index 0** (top of stack), NOT appends per Rules doc. Confirmed in fruit session. To get final top-down stack `[A, B, C]`, fire imports in REVERSE order: C → B → A. Last import ends at index 0 (top). The MCP Rules page documents "appended to end" — empirically false for image imports.
- **Rotation pivots at the layer's anchor** — in Creator UI that's image center; in builder JSON that's top-left. Prefer position bob over rotation for non-tilted motion either way.
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

**Fruit project** (orchard theme, ID `e065236d-aba4-4c73-aa86-aeeb1d7d7caa`):
- Combined BG file (back + front MERGED into one scene): https://creator.lottiefiles.com/new?workspace=cfaaeeca-95f3-4983-ae24-1b6eb132abc8&project=e065236d-aba4-4c73-aa86-aeeb1d7d7caa&fileId=128a2797-f640-47da-a1cc-2c9e3cc50e39
- Exception to back/front split: character cannot sit BETWEEN layers in this file. If app needs the split, request 2 separate Creator files later and re-import using same 8s/30fps motion table.

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

# Vegetable (farm/garden theme)
http://127.0.0.1:8765/preview-vegetable.html        # stacked (carrot placeholder)
http://127.0.0.1:8765/preview-vegetable-back.html   # back only
http://127.0.0.1:8765/preview-vegetable-front.html  # front only

# Fruit (orchard theme)
http://127.0.0.1:8765/preview-fruit.html            # stacked (apple placeholder)
http://127.0.0.1:8765/preview-fruit-back.html       # back only
http://127.0.0.1:8765/preview-fruit-front.html      # front only

# Transport (road/vehicle theme — 5/7 layers; road + signs pending regen)
http://127.0.0.1:8765/preview-transport.html        # stacked (school-bus placeholder)
http://127.0.0.1:8765/preview-transport-back.html   # back only
http://127.0.0.1:8765/preview-transport-front.html  # front only
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

## Vegetable variant motion table (current — farm/garden theme)
| Layer | Slot | Motion | Content |
|---|---|---|---|
| farm-sky (opaque) | sky | breathe ±5% | warm pastel sky w/ soft sun, no clouds-heavy |
| green-hills + crop-rows | hills | pan y -15 + breathe ±2% | rolling hills w/ neat crop-row stripes, tiny barn + windmill silhouettes |
| tall-trees / cypress cluster | trees | pan y -20 + breathe ±3% | mid-ground tall poplars / cypresses (no scarecrow / no character) |
| veggie-grass-strip | grass | pan y ±8 | bottom field band w/ carrot tops + beet greens + cabbage sprouts |
| garden-flowers + small-veggies | flowers | bob y ±15 | sunflower / wildflower clusters + small tomato / radish accents |
| butterflies + leaf-bits | particles | figure-8 ax=40 ay=60 | white butterflies + falling leaf-bits + dandelion seeds |

**Exclusion rule:** NO scarecrow, NO farmer, NO big basket-of-veggies — would compete with the child app's main vegetable character. Keep environment "empty stage" so the character carries focus.

## Fruit variant motion table (current — orchard theme, flat 2D cartoon)
| Layer | Slot | Motion | Content |
|---|---|---|---|
| ~~orchard-sky~~ | sky | — | DROPPED. PNG + webp still on disk but NOT in builder BACK list. App provides own background; transparent back.json gives flexibility. |
| orchard-hills | hills | pan y ±15 + breathe ±2% | 2 flat sage hill silhouettes |
| fruit-trees | trees | pan y ±20 + breathe ±3% | 5 round cartoon trees w/ apple+pear dots |
| ~~vines~~ | vines | — | NOT IMPLEMENTED (grape vines in top corners — skip or add) |
| grass-w-fallen-fruit | grass | pan y ±8 | bottom band w/ apples, pears, cherries on ground |
| ~~big-leaves~~ | big-leaves | — | DROPPED (was hanging banana/cherry clusters — removed for cleaner focal point) |
| blossoms | flowers | bob y ±15 | scattered 5-petal pink/white blossoms, yellow center |
| petals + butterflies + sparkles | particles | figure-8 ax=40 ay=60 | pink petals + yellow butterflies + white sparkle stars |

**Style note:** Flat 2D cartoon with locked 3-4 color palette per asset + thick black outlines (2-4px). NOT watercolor. Compresses to 7-40 KB per webp at q70/720w. Each prompt MUST include "NO gradients, NO shading, NO texture" + explicit hex palette.

**Exclusion rule:** NO fruit-character (no anthropomorphic apple/banana), NO big competing fruit clusters in front (big-leaves dropped for this reason). Character (kid + fruit pal) carries focus.

**Creator file note:** Fruit currently uses ONE combined BG file (back+front merged into single scene). All 6 image layers in same Lottie. Stack top→bottom: particles, flowers, grass, trees, hills, sky. Splitting into separate back/front would require 2 Creator files.

## Transport variant motion table (current — road/vehicle theme, 5/7 layers landed)
| Layer | Slot | Motion | Content |
|---|---|---|---|
| transport-sky (opaque) | sky | breathe ±5% | warm pastel daytime sky, smiling sun top-right, 2-3 clouds |
| transport-hills | hills | pan y ±15 + breathe ±2% | rolling green hills + tiny distant village (houses + church) — NO vehicles |
| transport-trees | trees | pan y ±20 + breathe ±3% | mid-ground oak + pine cluster |
| transport-grass | grass | pan y ±8 (y_offset +40) | bottom grass band + small bushes + wildflowers |
| transport-particles | particles | figure-8 ax=40 ay=60 | scattered birds + butterflies + dust puffs |
| **transport-road** | **road-curves** | **bob x ±10 (pending PNG)** | **winding asphalt road + dashed centerline — REGEN NEEDED** |
| **transport-signs** | **signs-poles** | **bob y ±6 (pending PNG)** | **lamp posts + blank signs + traffic light — REGEN NEEDED** |

**Exclusion rule:** NO vehicles in BG (cars/trucks/buses/trains/planes/firetrucks/bikes) — child app's main characters ARE the vehicles. Keep BG = empty stage so vehicle character carries focus. Also NO text/words on signs (kids audience, signs must be visually neutral).

**Style:** Soft flat watercolor (matches vegetable variant aesthetic), warm pastel sky palette to read as "happy daytime drive".
