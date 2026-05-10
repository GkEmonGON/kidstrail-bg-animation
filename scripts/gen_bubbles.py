"""Generate bubbles-particles.png — 1080x1920 transparent, bubbles + sparkles."""
import random
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
random.seed(42)

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)


def bubble(cx, cy, r):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # Soft interior tint
    ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(180, 230, 255, 28))
    # Outline ring (draw thicker by stacking)
    for w in (3, 2, 1):
        ld.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(255, 255, 255, 200 if w == 2 else 120),
            width=w,
        )
    # Highlight dot upper-left
    hr = max(2, int(r * 0.18))
    hx, hy = cx - int(r * 0.45), cy - int(r * 0.45)
    ld.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 255, 255, 230))
    # Small secondary highlight
    hr2 = max(1, int(r * 0.08))
    hx2, hy2 = cx + int(r * 0.35), cy + int(r * 0.30)
    ld.ellipse([hx2 - hr2, hy2 - hr2, hx2 + hr2, hy2 + hr2], fill=(255, 255, 255, 160))
    return layer


def sparkle(cx, cy, size):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    s = size
    # 4-point star via two thin diamonds
    ld.polygon(
        [(cx, cy - s), (cx + s * 0.25, cy), (cx, cy + s), (cx - s * 0.25, cy)],
        fill=(255, 255, 230, 220),
    )
    ld.polygon(
        [(cx - s, cy), (cx, cy - s * 0.25), (cx + s, cy), (cx, cy + s * 0.25)],
        fill=(255, 255, 230, 220),
    )
    # Center hot point
    ld.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(255, 255, 255, 255))
    return layer.filter(ImageFilter.GaussianBlur(radius=0.6))


# Bubbles — 28 of them, biased toward bottom-half rising
N_BUB = 28
for i in range(N_BUB):
    # Vertical bias toward lower 2/3 with some at top
    t = random.random()
    if t < 0.7:
        cy = int(H * (0.35 + random.random() * 0.6))
    else:
        cy = int(H * random.random())
    cx = int(80 + random.random() * (W - 160))
    # Size distribution: many small, few medium
    s = random.random()
    if s < 0.55:
        r = random.randint(8, 22)
    elif s < 0.9:
        r = random.randint(22, 42)
    else:
        r = random.randint(42, 65)
    b = bubble(cx, cy, r)
    img = Image.alpha_composite(img, b)

# Sparkles — 18 scattered
N_SPK = 18
for i in range(N_SPK):
    cx = int(40 + random.random() * (W - 80))
    cy = int(40 + random.random() * (H - 80))
    size = random.randint(8, 22)
    sp = sparkle(cx, cy, size)
    img = Image.alpha_composite(img, sp)

out = "assets/fish/front/bubbles-particles.png"
img.save(out, "PNG", optimize=True)
print(f"wrote {out} {img.size}")
