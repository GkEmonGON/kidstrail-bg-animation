"""Build fruit back.json + front.json Lottie. Embeds webps as data URIs."""
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
    return max(CANVAS_W / img_w, CANVAS_H / img_h) * zoom


def center_offset(img_w, img_h, scale):
    dw, dh = img_w * scale, img_h * scale
    return (-(dw - CANVAS_W) / 2, -(dh - CANVAS_H) / 2)


def linear_kfs(samples, frames):
    kfs = []
    for i, (t, val) in enumerate(samples):
        kf = {"t": t, "s": list(val)}
        if i < len(samples) - 1:
            kf["i"] = {"x": [1], "y": [1]}
            kf["o"] = {"x": [0], "y": [0]}
        kfs.append(kf)
    return kfs


def sine_pan_y(amp_y, n_kfs, base_xy):
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        y = base_xy[1] + math.sin(phase) * amp_y
        frames.append((t, [base_xy[0], y]))
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
    frames = []
    for i in range(n_kfs):
        t = round(OP * i / (n_kfs - 1))
        phase = 2 * math.pi * i / (n_kfs - 1)
        s = base_scale * (1 + math.sin(phase) * amp_pct / 100)
        frames.append((t, [s, s]))
    frames[-1] = (OP, list(frames[0][1]))
    return frames


def build_layer(ind, name, ref_id, img_w, img_h, motion):
    base_scale = cover_scale(img_w, img_h)
    ox, oy = center_offset(img_w, img_h, base_scale)
    ox += motion.get("x_offset", 0)
    oy += motion.get("y_offset", 0)

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


# BACK layers — front-to-back order in array (index 0 = top of stack)
BACK = [
    ("trees", ROOT / "assets/fruit/back-opt/trees.webp", m_pan_y_breathe(20, 3)),
    ("hills", ROOT / "assets/fruit/back-opt/hills.webp", m_pan_y_breathe(15, 2)),
    ("sky",   ROOT / "assets/fruit/back-opt/sky.webp",   m_breathe(5)),
]

# FRONT layers — front-to-back order in array (index 0 = top of stack)
FRONT = [
    ("particles", ROOT / "assets/fruit/front-opt/particles.webp", m_figure8(40, 60)),
    ("flowers",   ROOT / "assets/fruit/front-opt/flowers.webp",   m_bob_y(15)),
    ("grass",     ROOT / "assets/fruit/front-opt/grass.webp",     m_pan_y(8)),
]


if __name__ == "__main__":
    build_lottie(BACK,  ROOT / "assets/fruit/back.json")
    build_lottie(FRONT, ROOT / "assets/fruit/front.json")
