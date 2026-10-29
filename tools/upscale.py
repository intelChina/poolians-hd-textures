"""Upscale the scene / room textures with a resolution-aware factor.

Rules used by the shipped pack:

* max side <= 64   -> 8x
* max side <= 256  -> 4x
* otherwise        -> 2x
* BMP output is capped at 512 px (uncompressed BMPs grow quadratically)
* hard cap at 2048 px

Smooth sources (lightmaps, fake shadows, cube-map faces, sphere map) are
blurred instead of sharpened - inventing detail in a lighting map looks wrong.
"""
from __future__ import annotations

import os

from PIL import Image, ImageEnhance, ImageFilter

MAX_DIM = 2048
BMP_CAP = 512

SMOOTH = {
    "lightmap.jpg", "ball_shadow1.png", "ball_shadow12.png", "cue_shadow1.png",
    "spheremap.png", "cubemap1_bk.png", "cubemap1_dn.png", "cubemap1_fr.png",
    "cubemap1_lf.png", "cubemap1_rt.png", "cubemap1_up.png",
}

# never worth touching
SKIP = {"void.bmp", "chfoot.bmp", "aimpoint.png"}


def scale_factor(w: int, h: int, name: str) -> int:
    m = max(w, h)
    if m <= 64:
        k = 8
    elif m <= 256:
        k = 4
    else:
        k = 2
    while m * k > MAX_DIM and k > 1:
        k //= 2
    if name.lower().endswith(".bmp") and m * k > BMP_CAP:
        k = max(1, BMP_CAP // m)
    return max(1, k)


def upscale(name: str, data: bytes) -> tuple[Image.Image, tuple[int, int]]:
    """Return the upscaled image and its size, or the original if skipped."""
    im = Image.open(__import__("io").BytesIO(data))
    has_alpha = im.mode in ("RGBA", "LA", "P")
    im = im.convert("RGBA" if has_alpha else "RGB")
    w, h = im.size

    if name.lower() in SKIP:
        return im, im.size

    k = scale_factor(w, h, name)
    if k == 1:
        return im, im.size

    out = im.resize((w * k, h * k), Image.LANCZOS)
    if name in SMOOTH:
        out = out.filter(ImageFilter.GaussianBlur(0.35))
    else:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.4, percent=55, threshold=2))
        if not has_alpha:
            out = ImageEnhance.Contrast(out).enhance(1.04)
    return out, out.size


def save(out: Image.Image, path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bmp":
        out.convert("RGB").save(path, format="BMP")
    elif ext in (".jpg", ".jpeg"):
        out.convert("RGB").save(path, format="JPEG", quality=93, subsampling=0)
    else:
        out.save(path, format="PNG")
