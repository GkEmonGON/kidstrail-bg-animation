"""Build fish back.json + front.json Lottie. Embeds webps as data URIs."""
import base64
import json
import math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CANVAS_W, CANVAS_H = 1080, 1920
FR = 30
OP = 240  # 8s loop


def load_webp_b64(path: Path):
    raw = path.read_bytes()
    with Image.open(path) as im:
        w, h = im.size
    return f"data:image/webp;base64,{base64.b64encode(raw).decode()}", w, h


def cover_scale(img_w, img_h, zoom=1.15):
    """zoom=1.15 = over-cover (no edges visible); zoom=1.0 = exact cover (min overflow); <1.0 = letterbox."""
    return max(CANVAS_W / img_w, CANVAS_H / img_h) * zoom


def center_offset(img_w, img_h, scale):
    dw, dh = img_w * scale, img_h * scale
    return (-(dw - CANVAS_W) / 2, -(dh - CANVAS_H) / 2)


def linear_kfs(samples, frames):
    """samples is list of (frame, [x,y]) tuples. Linear easing between keyframes."""
    kfs = []
    for i, (t, val) in enumerate(samples):
        kf = {"t": t, "s": list(val)}
        if i < len(samples) - 1:
            kf["i"] = {"x": [1], "y": [1]}
            kf["o"] = {"x": [0], "y": [0]}
        kfs.append(kf)
    return kfs


def sine_pan_y(amp_y, n_kfs, base_xy):
    """pan vertical: y oscillates ±amp_y. Smooth via sine."""
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        y = base_xy[1] + math.sin(phase) * amp_y
        frames.append((t, [base_xy[0], y]))
    # ensure last == first for seamless loop
    frames[-1] = (OP, list(frames[0][1]))
    return frames


def sine_pan_x(amp_x, n_kfs, base_xy):
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        x = base_xy[0] + math.sin(phase) * amp_x
        frames.append((t, [x, base_xy[1]]))
    frames[-1] = (OP, list(frames[0][1]))
    return frames


def figure_eight(amp_x, amp_y, n_kfs, base_xy):
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        x = base_xy[0] + math.sin(phase) * amp_x
        y = base_xy[1] + math.sin(2 * phase) * amp_y
        frames.append((t, [x, y]))
    frames[-1] = (OP, list(frames[0][1]))
    return frames


def static_pos(base_xy):
    return [(0, list(base_xy)), (OP, list(base_xy))]


def breathe_scale(amp_pct, n_kfs, base_scale):
    """Scale sine pulse ±amp_pct of base_scale."""
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        s = base_scale * (1 + math.sin(phase) * amp_pct / 100)
        frames.append((t, [s, s]))
    frames[-1] = (OP, list(frames[0][1]))
    return frames


def build_layer(ind, name, ref_id, img_w, img_h, motion):
    """motion = dict with optional pan, scale, y_offset, x_offset, zoom, fit_mode, anchor keys.
    fit_mode: 'cover' (default, scale by max) | 'fit_width' (scale to canvas width, letterbox vert).
    anchor:   'center' (default) | 'top' | 'bottom' — only used when fit_mode='fit_width'.
    """
    fit_mode = motion.get("fit_mode", "cover")
    zoom = motion.get("zoom", 1.15)
    if fit_mode == "fit_width":
        base_scale = (CANVAS_W / img_w) * zoom
        disp_h = img_h * base_scale
        anchor = motion.get("anchor", "center")
        ox = (CANVAS_W - img_w * base_scale) / 2  # always 0 when zoom=1.0
        if anchor == "top":
            oy = 0
        elif anchor == "bottom":
            oy = CANVAS_H - disp_h
        else:
            oy = (CANVAS_H - disp_h) / 2
    else:
        base_scale = cover_scale(img_w, img_h, zoom=zoom)
        ox, oy = center_offset(img_w, img_h, base_scale)
    ox += motion.get("x_offset", 0)
    oy += motion.get("y_offset", 0)

    # Position
    pan = motion.get("pan")
    if pan == "static":
        pos_kfs = static_pos((ox, oy))
        pos_animated = False
    else:
        pos_kfs = pan(ox, oy)
        pos_animated = True

    if pos_animated:
        ks_p = {"a": 1, "k": linear_kfs(pos_kfs, OP)}
    else:
        ks_p = {"a": 0, "k": list(pos_kfs[0][1])}

    # Scale
    scale_pct = base_scale * 100
    scale_anim = motion.get("scale")
    if scale_anim:
        scale_kfs = scale_anim(scale_pct)
        ks_s = {"a": 1, "k": linear_kfs(scale_kfs, OP)}
    else:
        ks_s = {"a": 0, "k": [scale_pct, scale_pct]}

    return {
        "ddd": 0,
        "ind": ind,
        "ty": 2,
        "nm": name,
        "refId": ref_id,
        "sr": 1,
        "ks": {
            "o": {"a": 0, "k": 100},
            "r": {"a": 0, "k": 0},
            "p": ks_p,
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": ks_s,
        },
        "ao": 0,
        "ip": 0,
        "op": OP,
        "st": 0,
        "bm": 0,
    }


MAX_KB = 300


def build_lottie(layers_spec, out_path):
    """layers_spec: list of (name, webp_path, motion_dict). Index 0 = top (front-most)."""
    assets = []
    layers = []
    for i, (name, webp_path, motion) in enumerate(layers_spec):
        ref_id = f"img_{i}"
        data_uri, w, h = load_webp_b64(webp_path)
        assets.append({"id": ref_id, "w": w, "h": h, "u": "", "p": data_uri, "e": 1})
        layers.append(build_layer(i + 1, name, ref_id, w, h, motion))

    doc = {
        "v": "5.7.4",
        "fr": FR,
        "ip": 0,
        "op": OP,
        "w": CANVAS_W,
        "h": CANVAS_H,
        "nm": out_path.stem,
        "ddd": 0,
        "assets": assets,
        "layers": layers,
        "markers": [],
    }
    out_path.write_text(json.dumps(doc, separators=(",", ":")))
    size_kb = out_path.stat().st_size / 1024
    status = "OK" if size_kb <= MAX_KB else "OVER BUDGET"
    print(f"wrote {out_path} ({size_kb:.1f} KB) [{status} <= {MAX_KB} KB]")
    if size_kb > MAX_KB:
        raise SystemExit(f"ABORT: {out_path.name} = {size_kb:.1f} KB exceeds {MAX_KB} KB budget")


# ---- motion factories (return closure over base position) ----
def m_static():
    return {"pan": "static"}


def m_pan_y(amp):
    return {"pan": lambda ox, oy: sine_pan_y(amp, 17, (ox, oy))}


def m_pan_x(amp):
    return {"pan": lambda ox, oy: sine_pan_x(amp, 17, (ox, oy))}


def m_bob_y(amp):
    return {"pan": lambda ox, oy: sine_pan_y(amp, 21, (ox, oy))}


def m_bob_x(amp):
    return {"pan": lambda ox, oy: sine_pan_x(amp, 21, (ox, oy))}


def m_figure8(ax, ay):
    return {"pan": lambda ox, oy: figure_eight(ax, ay, 33, (ox, oy))}


def m_breathe(amp_pct):
    return {
        "pan": "static",
        "scale": lambda base: breathe_scale(amp_pct, 17, base),
    }


def m_pan_y_breathe(pan_amp, breathe_pct):
    return {
        "pan": lambda ox, oy: sine_pan_y(pan_amp, 17, (ox, oy)),
        "scale": lambda base: breathe_scale(breathe_pct, 17, base),
    }


# ---- BACK layers (front-to-back order in array) ----
# coral-cluster: fit_width + anchor top — content is in top corners, must preserve full horizontal extent. Water-bg behind fills any letterbox area.
BACK = [
    ("coral-cluster", ROOT / "assets/fish/back-opt/coral-cluster.webp", {**m_bob_x(10), "fit_mode": "fit_width", "anchor": "top", "zoom": 1.0}),
    ("kelp-forest",   ROOT / "assets/fish/back-opt/kelp-forest.webp",   m_pan_y_breathe(70, 3)),
    ("distant-reef",  ROOT / "assets/fish/back-opt/distant-reef.webp",  m_pan_y_breathe(50, 2)),
    ("water-bg",      ROOT / "assets/fish/back-opt/water-bg.webp",      m_breathe(5)),
]

# ---- FRONT layers (front-to-back order in array) ----
# fish-school REMOVED — would defocus main character fish placed by app on top of back.json
# big-seaweed: fit_width + anchor top — edge fronds must reach canvas left/right edges; transparent below is fine.
FRONT = [
    ("bubbles-particles", ROOT / "assets/fish/front-opt/bubbles-particles.webp", m_figure8(40, 60)),
    ("big-seaweed",       ROOT / "assets/fish/front-opt/big-seaweed.webp",       {**m_bob_y(6), "fit_mode": "fit_width", "anchor": "top", "zoom": 1.0}),
    # sand-floor: y_offset +40 to absorb ~74 px transparent padding in source PNG that would otherwise leave water-bg gap below sand at canvas bottom
    ("sand-floor",        ROOT / "assets/fish/front-opt/sand-floor.webp",        {**m_pan_y(8), "y_offset": 40}),
]


if __name__ == "__main__":
    build_lottie(BACK,  ROOT / "assets/fish/back.json")
    build_lottie(FRONT, ROOT / "assets/fish/front.json")
