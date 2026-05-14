#!/usr/bin/env python3
"""
Build animal-v2 back.json + front.json — slim 4-image variant (cost-conscious).
Canvas: square 1080x1080. Loop: 3s @ 30fps = 90 frames.
Motion library (visible amplitudes, no opacity-zero flicker):
  - static       (no keyframes)
  - breathe      (scale 100->102->100, very subtle base life)
  - wiggle       (rotation ±5°, 5 sine-sampled keyframes)
  - drift        (position figure-8 across ±150px, scale 95->105->95, opacity stays 100)
Layers used: back-base (full scene), front-big-leaf, front-butterfly, front-firefly.
"""
from __future__ import annotations
import base64, json, math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OPT  = ROOT / "assets" / "animal-v2" / "opt"
OUT  = ROOT / "assets" / "animal-v2"

W, H, FPS, DUR_S = 1080, 1080, 30, 3
OP = FPS * DUR_S                       # 90 frames
MAX_KB = 300


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")

def img_size(p: Path) -> tuple[int, int]:
    with Image.open(p) as im:
        return im.size

def img_content_bbox(p: Path) -> tuple[int, int, int, int]:
    """Return alpha-content bounding box (left, top, right, bottom). Fallback to full image."""
    with Image.open(p) as im:
        im = im.convert("RGBA")
        bbox = im.split()[-1].getbbox()
        if bbox is None:
            w, h = im.size
            return (0, 0, w, h)
        return bbox


# ---------- motion factories ----------
def m_static():
    return {}

def m_breathe(pct: float = 2.0, cycles: float = 1.0):
    """Scale pulse 100 -> 100+pct -> 100 (NEVER below 100, so bg can't shrink-expose stage).
    Uses (1+sin)/2 to stay in [0,1] range × pct, always added on top of 100."""
    pts = []
    samples = max(6, int(8 * cycles))
    for i in range(samples + 1):
        t = i * OP / samples
        v = 100 + pct * (1 + math.sin(2 * math.pi * cycles * t / OP)) / 2
        pts.append({"t": t, "s": [round(v, 2), round(v, 2)]})
    return {"scl_kfs": pts}

def m_wiggle(amp_deg: float, phase_frames: float = 0, cycles: float = 1.0,
             rot_offset: float = 0.0):
    """Rotation sine + optional baked-in tilt offset (degrees)."""
    pts = []
    samples = max(6, int(6 * cycles + 2))
    for i in range(samples + 1):
        t = i * OP / samples
        ang = rot_offset + amp_deg * math.sin(2 * math.pi * cycles * (t - phase_frames) / OP)
        pts.append({"t": t, "s": [round(ang, 3)]})
    return {"rot_kfs": pts}

def m_bob(start_xy, dx=0, dy=15, phase_frames=0, cycles=1.0):
    """Up-down bob (or side-side if dx != 0). Opacity stays 100."""
    sx, sy = start_xy
    pts = []
    samples = max(8, int(8 * cycles))
    for i in range(samples + 1):
        t = i * OP / samples
        a = 2 * math.pi * cycles * (t - phase_frames) / OP
        ox = dx * math.sin(a)
        oy = dy * math.sin(a)
        pts.append({"t": t, "s": [round(sx + ox, 2), round(sy + oy, 2), 0]})
    return {"pos_kfs": pts}

def m_drift(start_xy, dx, dy, phase_frames=0, scale_pulse=5, cycles=1.0):
    """Figure-8 drift around start. Scale pulse. Opacity stays 100."""
    sx, sy = start_xy
    pos_kfs = []
    samples = max(8, int(8 * cycles))
    for i in range(samples + 1):
        t = i * OP / samples
        a = 2 * math.pi * cycles * (t - phase_frames) / OP
        ox = dx * math.sin(a)
        oy = dy * math.sin(2 * a)
        pos_kfs.append({"t": t, "s": [round(sx + ox, 2), round(sy + oy, 2), 0]})
    scl_kfs = []
    for i in range(samples + 1):
        t = i * OP / samples
        v = 100 + scale_pulse * math.sin(2 * math.pi * cycles * (t - phase_frames) / OP)
        scl_kfs.append({"t": t, "s": [round(v, 2), round(v, 2)]})
    return {"pos_kfs": pos_kfs, "scl_kfs": scl_kfs}

def m_traverse(y, x_start, x_end):
    """Linear left-to-right (or any direction) traverse over full loop.
    Element is offscreen at both ends so loop snap at frame OP is invisible.
    """
    return {"pos_kfs": [
        {"t": 0,  "s": [x_start, y, 0]},
        {"t": OP, "s": [x_end,   y, 0]},
    ]}


# ---------- per-layer config ----------
# Ground line on back-base ≈ y=685. Tree-feet at y=800. Grass-bottom y=1020.
# Stack order: index 0 = TOP. Shadow rendered LATER in array (= BEHIND its element).
LAYERS_BACK = [
    # ===== BACK-LAYER BUTTERFLIES (client req: 3 butterflies in back + 3 in front for depth) =====
    {"name": "back-butterfly-1", "img": "front-butterfly.webp", "w": 90, "pos": (180, 540),
     "motion": m_drift((180, 540), dx=140, dy=80, phase_frames=14, scale_pulse=10, cycles=1.5)},
    {"name": "back-butterfly-2", "img": "front-butterfly.webp", "w": 75, "pos": (700, 520),
     "motion": m_drift((700, 520), dx=120, dy=70, phase_frames=42, scale_pulse=12, cycles=1.75)},
    {"name": "back-butterfly-3", "img": "front-butterfly.webp", "w": 65, "pos": (500, 600),
     "motion": m_drift((500, 600), dx=100, dy=60, phase_frames=68, scale_pulse=14, cycles=1.25)},
    # ===== MID-GROUND TREE BASE BUSH (RIGHT only — left moved to front per client) =====
    {"name": "tree-root-bush-R", "img": "back-bush.webp", "w": 360, "pos": (880, 845),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.5, phase_frames=37)},
    {"name": "shadow-tree-bush-R", "type": "shadow", "pos": (880, 850), "sw": 300, "sh": 30, "opa": 26},
    # ===== MID-GROUND TREES =====
    {"name": "back-tree-right",  "img": "back-tree-right.webp", "w": 380, "pos": (880, 820),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.5, phase_frames=25)},
    {"name": "back-tree-left",   "img": "back-tree-left.webp",  "w": 380, "pos": (210, 820),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.5, phase_frames=5)},
    {"name": "shadow-tree-right", "type": "shadow", "pos": (880, 830), "sw": 230, "sh": 26, "opa": 26},
    {"name": "shadow-tree-left",  "type": "shadow", "pos": (210, 830), "sw": 230, "sh": 26, "opa": 26},
    # ===== HANGING VINES =====
    {"name": "back-vine-right",  "img": "back-vine-right.webp", "w": 260, "pos": (950, -40),
     "anchor": "top", "motion": m_wiggle(amp_deg=5.0, phase_frames=8)},
    {"name": "back-vine-left",   "img": "back-vine-left.webp",  "w": 260, "pos": (130, -40),
     "anchor": "top", "motion": m_wiggle(amp_deg=5.0, phase_frames=42)},
    # ===== SKY =====
    {"name": "sky-cloud", "img": "sky-cloud.webp", "w": 240, "pos": (0, 170),
     "motion": m_traverse(y=170, x_start=-180, x_end=1260)},
    {"name": "sky-sun",   "img": "sky-sun.webp",   "w": 240, "pos": (220, 180),
     "motion": m_breathe(pct=5.0, cycles=2.0)},
    # ===== BASE (overscaled 1120 = 4% margin, breathe never shrinks below canvas size) =====
    {"name": "back-base", "img": "back-base.webp", "w": 1120, "pos": (540, 540),
     "motion": m_breathe(pct=1.5, cycles=1.0)},
]

# Reference pattern: MANY small foreground pieces. Spread across canvas bottom.
LAYERS_FRONT = [
    # ===== FLYING ACCENTS (in front of all decor) =====
    {"name": "firefly-1", "img": "front-firefly.webp", "w": 75, "pos": (760, 320),
     "motion": m_drift((760, 320), dx=140, dy=85, phase_frames=0,  scale_pulse=15, cycles=2.5)},
    {"name": "firefly-2", "img": "front-firefly.webp", "w": 65, "pos": (180, 280),
     "motion": m_drift((180, 280), dx=110, dy=70, phase_frames=18, scale_pulse=14, cycles=2.0)},
    {"name": "firefly-3", "img": "front-firefly.webp", "w": 55, "pos": (520, 230),
     "motion": m_drift((520, 230), dx=130, dy=60, phase_frames=37, scale_pulse=12, cycles=2.5)},
    {"name": "butterfly-1", "img": "front-butterfly.webp", "w": 110, "pos": (280, 470),
     "motion": m_drift((280, 470), dx=200, dy=110, phase_frames=0,  scale_pulse=10, cycles=1.5)},
    {"name": "butterfly-2", "img": "front-butterfly.webp", "w": 85,  "pos": (820, 410),
     "motion": m_drift((820, 410), dx=160, dy=95,  phase_frames=29, scale_pulse=12, cycles=1.75)},
    {"name": "butterfly-3", "img": "front-butterfly.webp", "w": 70,  "pos": (600, 380),
     "motion": m_drift((600, 380), dx=180, dy=80,  phase_frames=55, scale_pulse=14, cycles=1.25)},
    # ===== DENSE FOREGROUND DECOR =====
    # Stack order (top→bottom in array): grass+flowers ON TOP of bushes. Bushes anchor lowest at canvas bottom.
    # GRASS TUFTS (front-most, peek up from below canvas edge)
    {"name": "fr-grass-L1", "img": "front-grass-tuft.webp", "w": 220, "pos": (45, 1115),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=0,  rot_offset=-2)},
    {"name": "fr-grass-L2", "img": "front-grass-tuft.webp", "w": 150, "pos": (270, 1110),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=6.0, phase_frames=33, rot_offset=3)},
    {"name": "fr-grass-R1", "img": "front-grass-tuft.webp", "w": 180, "pos": (820, 1112),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=18, rot_offset=4)},
    {"name": "fr-grass-R2", "img": "front-grass-tuft.webp", "w": 160, "pos": (1015, 1118),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=6.5, phase_frames=49, rot_offset=-3)},
    # FLOWERS (on top of bushes)
    {"name": "fr-flower-L1", "img": "flower-cluster.webp", "w": 105, "pos": (75, 1040),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=3,  rot_offset=-4)},
    {"name": "fr-flower-L2", "img": "flower-cluster.webp", "w": 160, "pos": (215, 1050),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.5, phase_frames=27, rot_offset=3)},
    {"name": "fr-flower-L3", "img": "flower-cluster.webp", "w": 115, "pos": (370, 1030),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=51, rot_offset=-2)},
    {"name": "fr-flower-R1", "img": "flower-cluster.webp", "w": 140, "pos": (710, 1040),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=5.0, phase_frames=12, rot_offset=4)},
    {"name": "fr-flower-R2", "img": "flower-cluster.webp", "w": 100, "pos": (855, 1032),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.5, phase_frames=38, rot_offset=-5)},
    {"name": "fr-flower-R3", "img": "flower-cluster.webp", "w": 150, "pos": (1000, 1048),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=60, rot_offset=2)},
    # CORNER BIG LEAF (on top of bushes too)
    {"name": "front-big-leaf", "img": "front-big-leaf.webp", "w": 320, "pos": (1020, 1190),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=5.0, phase_frames=15, rot_offset=-6)},
    # BUSHES — bottom-most front layer, BIG, overlap each other to form continuous green carpet
    # LEFT bush row: 3 bushes overlapping, anchored to canvas bottom (y≈1090 = full height visible)
    {"name": "fr-bush-L1", "img": "back-bush.webp", "w": 300, "pos": (90,  1090),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=8,  rot_offset=-3)},
    {"name": "fr-bush-L2", "img": "back-bush.webp", "w": 270, "pos": (260, 1095),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.5, phase_frames=27, rot_offset=4)},
    {"name": "fr-bush-L3", "img": "back-bush.webp", "w": 230, "pos": (410, 1085),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=44, rot_offset=-2)},
    # RIGHT bush row: 3 bushes overlapping
    {"name": "fr-bush-R1", "img": "back-bush.webp", "w": 230, "pos": (680, 1085),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.8, phase_frames=15, rot_offset=2)},
    {"name": "fr-bush-R2", "img": "back-bush.webp", "w": 300, "pos": (860, 1095),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=36, rot_offset=-4)},
    {"name": "fr-bush-R3", "img": "back-bush.webp", "w": 270, "pos": (1020, 1090),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.5, phase_frames=58, rot_offset=3)},
    # ===== LION-PAW-COVER BUSH (client req v2: even bigger) =====
    {"name": "fr-paw-bush-L", "img": "back-bush.webp", "w": 490, "pos": (220, 1075),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.5, phase_frames=11)},
    {"name": "shadow-paw-bush-L", "type": "shadow", "pos": (220, 1080), "sw": 400, "sh": 36, "opa": 28},
    # ===== CORNER FILLERS (client req: fill gaps at bottom-left + bottom-right) =====
    # LEFT corner stack: small bush peeking + flower cluster + extra grass
    {"name": "fr-corner-bush-L", "img": "back-bush.webp", "w": 200, "pos": (10, 1020),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=29, rot_offset=-3)},
    {"name": "fr-corner-flower-L", "img": "flower-cluster.webp", "w": 110, "pos": (15, 985),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=7, rot_offset=-5)},
    {"name": "fr-corner-grass-L", "img": "front-grass-tuft.webp", "w": 140, "pos": (-10, 1075),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=24, rot_offset=-4)},
    # RIGHT corner stack
    {"name": "fr-corner-bush-R", "img": "back-bush.webp", "w": 200, "pos": (1070, 1020),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=51, rot_offset=4)},
    {"name": "fr-corner-flower-R", "img": "flower-cluster.webp", "w": 110, "pos": (1065, 985),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=41, rot_offset=5)},
    {"name": "fr-corner-grass-R", "img": "front-grass-tuft.webp", "w": 140, "pos": (1090, 1075),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=8, rot_offset=4)},
]


def kf_with_easing(kf, dims):
    """Add Lottie linear bezier easing to a keyframe; dims controls i/o array length."""
    return {**kf,
            "i": {"x": [0.5] * dims, "y": [0.5] * dims},
            "o": {"x": [0.5] * dims, "y": [0.5] * dims}}

def build_animatable(kfs, dims):
    return {"a": 1, "k": [kf_with_easing(kf, dims) for kf in kfs]}


def shadow_shape_layer(idx_id, name, pos_xy, size_w, size_h, opacity_pct=22):
    """Lottie type-4 shape layer = dark ellipse blob. Renders below element to ground it."""
    return {
        "ddd": 0, "ind": idx_id, "ty": 4, "nm": name, "sr": 1,
        "ks": {
            "p": {"a": 0, "k": [pos_xy[0], pos_xy[1], 0]},
            "r": {"a": 0, "k": 0},
            "s": {"a": 0, "k": [100, 100, 100]},
            "o": {"a": 0, "k": opacity_pct},
            "a": {"a": 0, "k": [0, 0, 0]},
        },
        "ao": 0,
        "shapes": [{
            "ty": "gr", "nm": "grp",
            "it": [
                {"ty": "el", "p": {"a": 0, "k": [0, 0]},
                 "s": {"a": 0, "k": [size_w, size_h]}, "d": 1, "nm": "ell"},
                {"ty": "fl", "c": {"a": 0, "k": [0, 0, 0, 1]},
                 "o": {"a": 0, "k": 100}, "r": 1, "nm": "fill"},
                {"ty": "tr",
                 "p": {"a": 0, "k": [0, 0]},
                 "a": {"a": 0, "k": [0, 0]},
                 "s": {"a": 0, "k": [100, 100]},
                 "r": {"a": 0, "k": 0},
                 "o": {"a": 0, "k": 100}, "nm": "tx"},
            ],
        }],
        "ip": 0, "op": OP, "st": 0, "bm": 0,
    }


def build_image_layer(idx_id, asset_id, name, w_src, h_src, target_w, pos, motion,
                      anchor_mode="center", content_bbox=None):
    base_scale = (target_w / w_src) * 100      # fit-to-target percentage
    # Use CONTENT bbox (not image bbox) so anchor lands on visible pixels.
    # Image-pixel coords. Rotation/scale pivots here.
    cb = content_bbox or (0, 0, w_src, h_src)
    cx = (cb[0] + cb[2]) / 2          # content horizontal center
    if anchor_mode == "top":
        anchor = [cx, cb[1], 0]       # content top edge
    elif anchor_mode == "bottom":
        anchor = [cx, cb[3], 0]       # content bottom edge
    else:
        anchor = [cx, (cb[1] + cb[3]) / 2, 0]  # content center

    # scale: 2D pulse percentage from motion -> multiply by base_scale -> 3D Lottie value
    if motion.get("scl_kfs"):
        scl_kfs_3d = [
            {**kf, "s": [kf["s"][0] * base_scale / 100,
                         kf["s"][1] * base_scale / 100,
                         100]}
            for kf in motion["scl_kfs"]
        ]
        scl_anim = build_animatable(scl_kfs_3d, 3)
    else:
        scl_anim = {"a": 0, "k": [base_scale, base_scale, 100]}

    ks = {
        "p": build_animatable(motion["pos_kfs"], 3) if motion.get("pos_kfs") else
             {"a": 0, "k": [pos[0], pos[1], 0]},
        "r": build_animatable(motion["rot_kfs"], 1) if motion.get("rot_kfs") else
             {"a": 0, "k": 0},
        "s": scl_anim,
        "o": {"a": 0, "k": 100},
        "a": {"a": 0, "k": anchor},
    }
    return {
        "ddd": 0, "ind": idx_id, "ty": 2, "nm": name, "refId": asset_id,
        "sr": 1, "ks": ks, "ao": 0, "ip": 0, "op": OP, "st": 0, "bm": 0,
    }


def build_lottie(layer_specs, out_name):
    assets, layers = [], []
    asset_by_img: dict[str, tuple[str, int, int]] = {}
    for i, spec in enumerate(layer_specs):
        if spec.get("type") == "shadow":
            layers.append(shadow_shape_layer(
                idx_id=i + 1, name=spec["name"],
                pos_xy=spec["pos"], size_w=spec["sw"], size_h=spec["sh"],
                opacity_pct=spec.get("opa", 22),
            ))
            continue
        fname = spec["img"]
        if fname not in asset_by_img:
            img_path = OPT / fname
            w_src, h_src = img_size(img_path)
            cbbox = img_content_bbox(img_path)
            asset_id = f"img_{len(assets)}"
            asset_by_img[fname] = (asset_id, w_src, h_src, cbbox)
            assets.append({
                "id": asset_id, "w": w_src, "h": h_src,
                "u": "", "p": f"data:image/webp;base64,{b64(img_path)}", "e": 1,
            })
        asset_id, w_src, h_src, cbbox = asset_by_img[fname]
        layers.append(build_image_layer(
            idx_id=i + 1, asset_id=asset_id,
            name=spec["name"], w_src=w_src, h_src=h_src,
            target_w=spec["w"], pos=spec["pos"], motion=spec["motion"],
            anchor_mode=spec.get("anchor", "center"),
            content_bbox=cbbox,
        ))
    doc = {
        "v": "5.7.4", "fr": FPS, "ip": 0, "op": OP, "w": W, "h": H,
        "nm": out_name, "ddd": 0, "assets": assets, "layers": layers,
        "meta": {"g": "kidstrail-animal-v2"},
    }
    out_path = OUT / f"{out_name}.json"
    out_path.write_text(json.dumps(doc, separators=(",", ":")))
    return out_path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for spec_list, name in [(LAYERS_BACK, "back"), (LAYERS_FRONT, "front")]:
        p = build_lottie(spec_list, name)
        size_kb = p.stat().st_size / 1024
        flag = "OK" if size_kb <= MAX_KB else "OVER"
        print(f"[{flag}] {p.name}  {size_kb:.1f} KB  layers={len(spec_list)}")
        if size_kb > MAX_KB:
            raise SystemExit(f"Hard cap exceeded ({size_kb:.1f} > {MAX_KB} KB)")
    return 0


if __name__ == "__main__":
    main()
