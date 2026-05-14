#!/usr/bin/env python3
"""
Build bird-v2 back.json + front.json — SKY-themed variant.
Canvas: square 1080x1080. Loop: 3s @ 30fps = 90 frames.
Follows client patterns from build_lessons.md:
- Char type: airborne -> width 40-60%, top:35-50% (smaller than animal lion)
- Depth-pair: 3 small-birds in back + 3 in front (smaller in back)
- Foreground depth-contact: hanging perch-branch from top (bird perches near it)
- Corner stacks: 3-piece bush+flower+grass on each bottom corner (reused from animal-v2)
"""
from __future__ import annotations
import base64, json, math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OPT  = ROOT / "assets" / "bird-v2" / "opt"
OUT  = ROOT / "assets" / "bird-v2"

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
# Bird = airborne char. Sky takes upper 75% of canvas, hills 25% at bottom.
# Char goes top:40% with width 40-55% (smaller than ground subject).
LAYERS_BACK = [
    # ===== BACK depth-pair small-birds (HIGHLY varied speeds + pause delays) =====
    # PNG bird faces LEFT. mirror=True → faces RIGHT.
    # bird-1: VERY FAST L→R (zooms across, 2200px range)
    {"name": "back-small-bird-1", "img": "bird-small-flying-bird.webp", "w": 85,
     "pos": (-400, 380), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-500, 380, 0]},
         {"t": 90, "s": [1700, 360, 0]},
     ]}},
    # bird-2: SLOW R→L with DELAYED start (sits offscreen 20f then crawls across)
    {"name": "back-small-bird-2", "img": "bird-small-flying-bird.webp", "w": 70,
     "pos": (1300, 250),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [1300, 240, 0]},
         {"t": 20, "s": [1300, 240, 0]},   # paused offscreen-right
         {"t": 90, "s": [-200, 270, 0]},
     ]}},
    # bird-3: MEDIUM L→R, early entry then EXTRA-LONG glide before exit
    {"name": "back-small-bird-3", "img": "bird-small-flying-bird.webp", "w": 60,
     "pos": (-150, 480), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-150, 460, 0]},
         {"t": 30, "s": [120, 470, 0]},     # slow start
         {"t": 90, "s": [1280, 500, 0]},
     ]}},
    # ===== CHASE PAIR (synced, A leads, B chases — KEEP SAME SPEED for chase look) =====
    # Mid-speed chase: 1500px range, slight stagger
    {"name": "back-chase-A", "img": "bird-small-flying-bird.webp", "w": 75,
     "pos": (-200, 320), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-200, 320, 0]},
         {"t": 90, "s": [1300, 320, 0]},
     ]}},
    {"name": "back-chase-B", "img": "bird-small-flying-bird.webp", "w": 65,
     "pos": (-340, 350), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-340, 350, 0]},
         {"t": 90, "s": [1160, 350, 0]},
     ]}},
    # ===== EXTRA RANDOMIZED BIRDS (varied sizes + speeds + spatial offsets to spread temporally) =====
    # bird-extra-1: starts MID-LOOP position (at canvas-x=450 at t=0) — invisible-snap at frame 90
    # Achieved by setting END position to start + offscreen-exit, then loop back: -100 → 1500 over 90f
    # At t=0 already at x=-100 (offscreen), enters canvas around t=6, exits ~t=66
    {"name": "back-bird-x1", "img": "bird-small-flying-bird.webp", "w": 48,
     "pos": (-100, 200), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-100, 210, 0]},
         {"t": 90, "s": [1500, 190, 0]},
     ]}},
    # bird-extra-2: TINY + fast R→L, different y band (high), starts further offscreen for late entry
    {"name": "back-bird-x2", "img": "bird-small-flying-bird.webp", "w": 42,
     "pos": (1500, 160),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [1500, 150, 0]},
         {"t": 40, "s": [1500, 150, 0]},  # offscreen pause until t=40 (different respawn time)
         {"t": 90, "s": [-300, 170, 0]},
     ]}},
    # bird-extra-3: MEDIUM size, low altitude, slow with double-pause for stop-and-go feel
    {"name": "back-bird-x3", "img": "bird-small-flying-bird.webp", "w": 78,
     "pos": (-200, 540), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-200, 530, 0]},
         {"t": 25, "s": [200, 545, 0]},
         {"t": 50, "s": [350, 530, 0]},   # near-pause mid-canvas
         {"t": 90, "s": [1300, 550, 0]},  # bursts to exit
     ]}},
    # ===== SMALL FAR-DISTANCE LEAVES (back-layer depth-pair, WILD chaos rotations) =====
    # back-leaf-far-1: 50f FAST fall, big L-curve drift, 360° full spin
    {"name": "back-leaf-far-1", "img": "falling-leaf.webp", "w": 55,
     "pos": (440, -120),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [440, -120, 0]},
         {"t": 15, "s": [550, 120, 0]},
         {"t": 35, "s": [380, 600, 0]},
         {"t": 50, "s": [490, 1180, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 25, "s": [180]},
         {"t": 50, "s": [360]},   # full spin during fall
         {"t": 90, "s": [360]},   # hold once offscreen
     ]}},
    # back-leaf-far-2: 35f pause, then 55f tumble fall with -2x spin (reverse direction)
    {"name": "back-leaf-far-2", "img": "falling-leaf.webp", "w": 70,
     "pos": (640, -180),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [640, -180, 0]},
         {"t": 35, "s": [640, -180, 0]},
         {"t": 55, "s": [780, 300, 0]},
         {"t": 75, "s": [550, 700, 0]},
         {"t": 90, "s": [700, 1200, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 35, "s": [0]},
         {"t": 60, "s": [-120]},
         {"t": 90, "s": [-280]},  # reverse spin
     ]}},
    # ===== CLOUDS scattered (REPOSITIONED to not overlap sun) =====
    # cloud-traverse y=240 (was 200) — below sun zone
    {"name": "back-cloud-traverse", "img": "sky-cloud.webp", "w": 220, "pos": (0, 240),
     "motion": m_traverse(y=240, x_start=-200, x_end=1280)},
    # cloud-1 moved RIGHT-of-sun (was at 200,150 — collided with sun)
    {"name": "back-cloud-1", "img": "bird-cloud-soft.webp", "w": 220, "pos": (500, 130),
     "motion": m_bob((500, 130), dx=20, dy=10, phase_frames=15, cycles=0.5)},
    {"name": "back-cloud-2", "img": "bird-cloud-soft.webp", "w": 200, "pos": (880, 280),
     "motion": m_bob((880, 280), dx=15, dy=8,  phase_frames=40, cycles=0.5)},
    # ===== SUN =====
    {"name": "sky-sun", "img": "sky-sun.webp", "w": 220, "pos": (180, 170),
     "motion": m_breathe(pct=5.0, cycles=2.0)},
    # ===== BASE (overscaled 1120 = 4% margin) =====
    {"name": "back-base", "img": "bird-back-base.webp", "w": 1120, "pos": (540, 540),
     "motion": m_breathe(pct=1.5, cycles=1.0)},
]

# Reference pattern: MANY small foreground pieces. Spread across canvas bottom.
LAYERS_FRONT = [
    # ===== FRONT depth-pair small-birds (HIGHLY varied speeds) =====
    # bird-1: MEDIUM L→R with y wobble, larger size closer to viewer
    {"name": "front-small-bird-1", "img": "bird-small-flying-bird.webp", "w": 140,
     "pos": (-200, 380), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-200, 400, 0]},
         {"t": 30, "s": [220, 360, 0]},
         {"t": 60, "s": [700, 410, 0]},
         {"t": 90, "s": [1280, 370, 0]},
     ]}},
    # bird-2: VERY FAST R→L (zooms across, 2000px range = 22 px/f)
    {"name": "front-small-bird-2", "img": "bird-small-flying-bird.webp", "w": 120,
     "pos": (1500, 470),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [1500, 480, 0]},
         {"t": 90, "s": [-500, 440, 0]},
     ]}},
    # bird-3: SLOWEST — long ride with pause then accelerates offscreen
    {"name": "front-small-bird-3", "img": "bird-small-flying-bird.webp", "w": 110,
     "pos": (-200, 250), "mirror": True,
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [-200, 220, 0]},
         {"t": 40, "s": [200, 280, 0]},     # crawls forward
         {"t": 70, "s": [400, 250, 0]},     # mid-canvas (lingers)
         {"t": 90, "s": [1180, 270, 0]},    # speeds up, exits offscreen-right
     ]}},
    # ===== FOREGROUND CLOUD (close, in front of char, slightly slow drift) =====
    {"name": "fr-cloud-foreground", "img": "sky-cloud.webp", "w": 280, "pos": (980, 380),
     "motion": m_bob((980, 380), dx=30, dy=12, phase_frames=20, cycles=0.5)},
    # ===== PERCH-BRANCH RIGHT (depth-contact, extends OFFSCREEN-RIGHT) =====
    {"name": "fr-perch-branch-R", "img": "bird-perch-branch.webp", "w": 620, "pos": (1080, -40),
     "anchor": "top", "motion": m_wiggle(amp_deg=3.0, phase_frames=12)},
    # ===== PERCH-BRANCH LEFT (mirrored, extends OFFSCREEN-LEFT) =====
    {"name": "fr-perch-branch-L", "img": "bird-perch-branch.webp", "w": 520, "pos": (0, -20),
     "anchor": "top", "mirror": True, "motion": m_wiggle(amp_deg=3.0, phase_frames=42)},
    # ===== FALLING LEAVES (top→bottom only, WILD chaos: huge x-drifts + spins + varied speeds) =====
    # leaf-1: medium 110 — slow 90f fall, big zigzag x-drift, double-spin
    {"name": "fr-falling-leaf-1", "img": "falling-leaf.webp", "w": 110,
     "pos": (340, -100),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [340, -100, 0]},
         {"t": 20, "s": [180, 120, 0]},   # zags LEFT
         {"t": 45, "s": [420, 400, 0]},   # zigs RIGHT
         {"t": 70, "s": [240, 750, 0]},   # zags LEFT again
         {"t": 90, "s": [380, 1180, 0]},  # exits
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 45, "s": [360]},
         {"t": 90, "s": [720]},   # 2 full spins
     ]}},
    # leaf-2: medium 90 — pause 20f, then 70f S-curve fall with REVERSE spin
    {"name": "fr-falling-leaf-2", "img": "falling-leaf.webp", "w": 90,
     "pos": (760, -180),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [760, -180, 0]},
         {"t": 20, "s": [760, -180, 0]},
         {"t": 45, "s": [930, 280, 0]},   # drifts right
         {"t": 70, "s": [620, 700, 0]},   # then left
         {"t": 90, "s": [800, 1180, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 45, "s": [-180]},
         {"t": 90, "s": [-540]},  # 1.5 reverse spins
     ]}},
    # leaf-3: small 60 — pause 40f, then 50f FAST fall, tight rotation wobble
    {"name": "fr-falling-leaf-3", "img": "falling-leaf.webp", "w": 60,
     "pos": (170, -200),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [170, -200, 0]},
         {"t": 40, "s": [170, -200, 0]},
         {"t": 60, "s": [330, 280, 0]},   # drifts right
         {"t": 90, "s": [80, 1180, 0]},   # drifts hard LEFT
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 50, "s": [70]},
         {"t": 70, "s": [-40]},
         {"t": 90, "s": [90]},
     ]}},
    # leaf-4: large 130 — slow 90f fall, dramatic S-sway, gentle ±90° wobble (no full spin)
    {"name": "fr-falling-leaf-4", "img": "falling-leaf.webp", "w": 130,
     "pos": (920, -120),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [920, -120, 0]},
         {"t": 22, "s": [780, 100,  0]},  # drift LEFT
         {"t": 45, "s": [990, 400,  0]},  # drift RIGHT
         {"t": 68, "s": [820, 700,  0]},  # drift LEFT again
         {"t": 90, "s": [970, 1180, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [-30]},
         {"t": 30, "s": [90]},
         {"t": 60, "s": [-90]},
         {"t": 90, "s": [60]},
     ]}},
    # leaf-5: medium 95 — pause 25f, then mid-speed fall, DOUBLE-spin tumble
    {"name": "fr-falling-leaf-5", "img": "falling-leaf.webp", "w": 95,
     "pos": (530, -180),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [530, -180, 0]},
         {"t": 25, "s": [530, -180, 0]},
         {"t": 55, "s": [670, 380, 0]},   # right
         {"t": 80, "s": [400, 850, 0]},   # left
         {"t": 90, "s": [510, 1180, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 45, "s": [-360]},
         {"t": 90, "s": [-720]},  # 2 reverse spins
     ]}},
    # ===== FOREGROUND BIG LEAVES (closer to viewer = bigger = chaotic) =====
    # big-leaf-1: w=200, MASSIVE x-drift ±250px, FULL 360° spin
    {"name": "fr-big-leaf-1", "img": "falling-leaf.webp", "w": 200,
     "pos": (180, -250),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [180, -250, 0]},
         {"t": 22, "s": [380, 80,  0]},   # +200 right
         {"t": 50, "s": [50, 480,  0]},   # -330 left (huge swing)
         {"t": 75, "s": [310, 850, 0]},   # +260 right
         {"t": 90, "s": [120, 1200, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [0]},
         {"t": 30, "s": [180]},
         {"t": 60, "s": [-90]},
         {"t": 90, "s": [270]},
     ]}},
    # big-leaf-2: w=180, pause 15f, GENTLE pendulum swing -45° to +45° (heavy leaf feel)
    {"name": "fr-big-leaf-2", "img": "falling-leaf.webp", "w": 180,
     "pos": (850, -200),
     "motion": {"pos_kfs": [
         {"t": 0,  "s": [850, -200, 0]},
         {"t": 15, "s": [850, -200, 0]},
         {"t": 40, "s": [980, 150, 0]},
         {"t": 65, "s": [720, 600, 0]},   # big leftward swing
         {"t": 90, "s": [890, 1200, 0]},
     ], "rot_kfs": [
         {"t": 0,  "s": [45]},
         {"t": 30, "s": [-45]},
         {"t": 60, "s": [60]},
         {"t": 90, "s": [-30]},
     ]}},
    # ===== GROUND-STRIP DECOR (small, only at bottom 25% since sky dominates) =====
    # Grass tufts (front-most, peek from bottom)
    {"name": "fr-grass-L1", "img": "front-grass-tuft.webp", "w": 180, "pos": (60, 1115),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=0,  rot_offset=-2)},
    {"name": "fr-grass-R1", "img": "front-grass-tuft.webp", "w": 160, "pos": (1020, 1118),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=6.5, phase_frames=22, rot_offset=3)},
    {"name": "fr-grass-mid", "img": "front-grass-tuft.webp", "w": 130, "pos": (520, 1110),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=6.0, phase_frames=44, rot_offset=-3)},
    # Flowers scattered along ground strip
    {"name": "fr-flower-L1", "img": "flower-cluster.webp", "w": 100, "pos": (130, 1040),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=8,  rot_offset=-4)},
    {"name": "fr-flower-L2", "img": "flower-cluster.webp", "w": 90,  "pos": (350, 1050),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.5, phase_frames=30, rot_offset=3)},
    {"name": "fr-flower-R1", "img": "flower-cluster.webp", "w": 105, "pos": (760, 1040),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=18, rot_offset=4)},
    {"name": "fr-flower-R2", "img": "flower-cluster.webp", "w": 95,  "pos": (940, 1050),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.5, phase_frames=56, rot_offset=-5)},
    # Bushes — MIX of round (back-bush) + tall-teardrop (back-bush-2) for variety
    {"name": "fr-bush-L1", "img": "back-bush.webp",   "w": 220, "pos": (130, 1090),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=8,  rot_offset=-3)},
    {"name": "fr-bush-L2", "img": "back-bush-2.webp", "w": 180, "pos": (320, 1085),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.8, phase_frames=33, rot_offset=4)},
    {"name": "fr-bush-R1", "img": "back-bush-2.webp", "w": 200, "pos": (770, 1090),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=2.5, phase_frames=18, rot_offset=2)},
    {"name": "fr-bush-R2", "img": "back-bush.webp",   "w": 240, "pos": (970, 1095),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=48, rot_offset=-3)},
    # ===== CORNER FILLERS (rule: 3-piece stack at each bottom corner) =====
    # LEFT corner stack (uses back-bush-2 for variety in corners)
    {"name": "fr-corner-bush-L", "img": "back-bush-2.webp", "w": 180, "pos": (10, 1020),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=29, rot_offset=-3)},
    {"name": "fr-corner-flower-L", "img": "flower-cluster.webp", "w": 100, "pos": (15, 985),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=7, rot_offset=-5)},
    {"name": "fr-corner-grass-L", "img": "front-grass-tuft.webp", "w": 130, "pos": (-10, 1075),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=7.0, phase_frames=24, rot_offset=-4)},
    # RIGHT corner stack (uses round back-bush for contrast with bush-2 on left)
    {"name": "fr-corner-bush-R", "img": "back-bush.webp", "w": 180, "pos": (1070, 1020),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=3.0, phase_frames=51, rot_offset=4)},
    {"name": "fr-corner-flower-R", "img": "flower-cluster.webp", "w": 100, "pos": (1065, 985),
     "anchor": "bottom", "motion": m_wiggle(amp_deg=4.0, phase_frames=41, rot_offset=5)},
    {"name": "fr-corner-grass-R", "img": "front-grass-tuft.webp", "w": 130, "pos": (1090, 1075),
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
                      anchor_mode="center", content_bbox=None, mirror=False):
    base_scale = (target_w / w_src) * 100      # fit-to-target percentage
    # Use CONTENT bbox (not image bbox) so anchor lands on visible pixels.
    cb = content_bbox or (0, 0, w_src, h_src)
    cx = (cb[0] + cb[2]) / 2
    if anchor_mode == "top":
        anchor = [cx, cb[1], 0]
    elif anchor_mode == "bottom":
        anchor = [cx, cb[3], 0]
    else:
        anchor = [cx, (cb[1] + cb[3]) / 2, 0]
    # mirror = horizontal flip via negative scale_x
    sx_sign = -1 if mirror else 1

    # scale: 2D pulse percentage from motion -> multiply by base_scale -> 3D Lottie value
    if motion.get("scl_kfs"):
        scl_kfs_3d = [
            {**kf, "s": [kf["s"][0] * base_scale / 100 * sx_sign,
                         kf["s"][1] * base_scale / 100,
                         100]}
            for kf in motion["scl_kfs"]
        ]
        scl_anim = build_animatable(scl_kfs_3d, 3)
    else:
        scl_anim = {"a": 0, "k": [base_scale * sx_sign, base_scale, 100]}

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
            mirror=spec.get("mirror", False),
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
