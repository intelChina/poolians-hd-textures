"""Procedurally regenerate the 16 pool-ball textures at higher resolution.

The stock textures are 128x128 bitmaps that only contain a flat body colour
(or a coloured band for 9-15), a white patch and a serif number.  Regenerating
them with 4x supersampling gives a much cleaner edge than upscaling ever could.

Layout constants below were measured from the original 128x128 textures:

* white patch:  centre (64.5, 62.5), radius 20.5 px
* number ink:   ~26 px tall, centred on (64.5, 61.5)
* stripe band:  rows 39..86 (for balls 9-15)

Colours are sampled from the corresponding stock texture so the palette stays
faithful to the original art direction.
"""
from __future__ import annotations

import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 512
SUPERSAMPLE = 4
SEED = 1234

# geometry in 128px reference space
REF = 128.0
DISC_CX, DISC_CY, DISC_R = 64.5, 62.5, 20.5
NUM_H = 26.0
NUM_CX, NUM_CY = 64.5, 61.5
BAND_TOP, BAND_BOT = 39.0, 86.0

SOLID = {
    1: (241, 206, 87), 2: (50, 50, 137), 3: (204, 51, 0), 4: (116, 94, 115),
    5: (226, 117, 20), 6: (55, 98, 55), 7: (153, 94, 87), 8: (0, 0, 0),
}
STRIPE = {
    9: (241, 209, 84), 10: (50, 50, 137), 11: (189, 58, 15), 12: (116, 94, 115),
    13: (226, 117, 20), 14: (55, 98, 55), 15: (153, 94, 87),
}

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\timesbd.ttf",
    r"C:\Windows\Fonts\georgiab.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.truetype("DejaVuSerif-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _number_mask(num: int, ink_height: float, supersample: int) -> Image.Image:
    """Render *num* so its ink is exactly *ink_height* pixels tall (pre-supersample)."""
    probe = _load_font(200)
    box = probe.getbbox(str(num))
    ink = box[3] - box[1]
    font = _load_font(max(4, int(round(200 * ink_height * supersample / ink))))
    box = font.getbbox(str(num))
    w, h = box[2] - box[0], box[3] - box[1]
    img = Image.new("L", (w + 8, h + 8), 0)
    ImageDraw.Draw(img).text((4 - box[0], 4 - box[1]), str(num), font=font, fill=255)
    return img


def _grain(size: int, sigma: float = 12.0, seed: int = SEED) -> Image.Image:
    rng = random.Random(seed)
    data = bytes(min(255, max(0, int(rng.gauss(128, sigma)))) for _ in range(size * size))
    return Image.frombytes("L", (size, size), data).filter(ImageFilter.GaussianBlur(0.6))


def make_ball(num: int, cue_src: Image.Image | None = None) -> Image.Image:
    """Return a 512x512 RGB texture for ball *num* (0 = cue ball)."""
    k = SIZE / REF

    if num == 0:
        if cue_src is None:
            return Image.new("RGB", (SIZE, SIZE), (252, 252, 250))
        im = cue_src.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
        return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=45, threshold=2))

    stripe = num in STRIPE
    colour = STRIPE[num] if stripe else SOLID[num]

    W = SIZE * SUPERSAMPLE
    img = Image.new("RGB", (W, W), (255, 255, 255) if stripe else colour)
    draw = ImageDraw.Draw(img)
    if stripe:
        draw.rectangle([0, BAND_TOP * k * SUPERSAMPLE, W, BAND_BOT * k * SUPERSAMPLE], fill=colour)

    cx, cy, r = DISC_CX * k, DISC_CY * k, DISC_R * k
    draw.ellipse([(cx - r) * SUPERSAMPLE, (cy - r) * SUPERSAMPLE,
                  (cx + r) * SUPERSAMPLE, (cy + r) * SUPERSAMPLE], fill=(255, 255, 255))

    mask = _number_mask(num, NUM_H * k, SUPERSAMPLE)
    mw, mh = mask.size
    img.paste((8, 8, 8), (int(NUM_CX * k * SUPERSAMPLE - mw / 2),
                          int(NUM_CY * k * SUPERSAMPLE - mh / 2)), mask)
    img = img.resize((SIZE, SIZE), Image.LANCZOS)

    # keep a hint of the felt-like grain the originals have
    if num != 8:
        grain = _grain(SIZE, seed=SEED + num)
        img = Image.blend(img, Image.merge("RGB", (grain, grain, grain)), 0.035)
    return img


def build_set(out_dir: str, cue_src_path: str | None = None) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    cue = Image.open(cue_src_path) if cue_src_path and os.path.isfile(cue_src_path) else None
    written = []
    for num in range(16):
        path = os.path.join(out_dir, "ball%d.bmp" % num)
        make_ball(num, cue).save(path, format="BMP")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Regenerate pool-ball textures")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--cue", help="original ball0.bmp to upscale as the cue ball")
    args = ap.parse_args(argv)
    files = build_set(args.out, args.cue)
    print("wrote %d textures to %s" % (len(files), args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
