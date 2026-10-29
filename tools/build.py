"""Build the HD texture pack from a local (legally owned) game installation.

Nothing copyrighted is shipped with this repository: the tool reads the
original ``.pak`` archives that are already on your disk, regenerates the
textures, and writes new ``.pak`` files.

    python build.py --game "C:/Program Files (x86)/Steam/steamapps/common/Real Pool 3D" --out build
    python build.py --game "..." --out build --zip        # also produce a drop-in zip
    python build.py --game "..." --out build --install    # write straight into the game

If a ``<pak>.backup`` file sits next to a pak, it is used as the pristine
source, so the tool can be re-run after installing the mod.
"""
from __future__ import annotations

import io
import os
import shutil
import struct
import zipfile

import balls
import materials
import pakcodec
import upscale

GAMES = ("RealPool3D", "RealSnooker3D")
PAKS = ("common.pak", "room1.pak")
IMAGE_EXT = (".bmp", ".png", ".jpg", ".jpeg")
BALLS = {"ball%d.bmp" % i for i in range(16)}
# a pristine copy of the pak, if the mod has already been installed once
BACKUP_SUFFIXES = (".backup", ".dsh_backup", ".orig")


def pristine_source(live: str) -> str:
    for suffix in BACKUP_SUFFIXES:
        if os.path.isfile(live + suffix):
            return live + suffix
    return live


def process_pak(game: str, src_pak: str, cue_src, regenerate_balls: bool) -> tuple[bytes, int, dict]:
    """Return (new_pak_blob, replaced_count, stats)."""
    zf = pakcodec.open_pak(src_pak)
    buf = io.BytesIO()
    replaced = 0
    stats = {"texture": 0, "material": 0, "ball": 0}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as dst:
        for info in zf.infolist():
            name = info.filename
            data = zf.read(name)
            low = name.lower()

            if name in materials.PATCHERS:
                data = materials.patch(name, data.decode("latin1")).encode("latin1")
                stats["material"] += 1
                replaced += 1
            elif low.endswith(IMAGE_EXT) and low not in upscale.SKIP:
                if regenerate_balls and low in BALLS:
                    image = balls.make_ball(int(low[4:-4]), cue_src)
                    data = _to_bmp(image)
                    stats["ball"] += 1
                else:
                    image, _ = upscale.upscale(name, data)
                    data = _encode(name, image)
                    stats["texture"] += 1
                replaced += 1

            zi = zipfile.ZipInfo(name, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            dst.writestr(zi, data)
    zf.close()
    return buf.getvalue(), replaced, stats


def _to_bmp(image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="BMP")
    return buf.getvalue()


def _encode(name: str, image) -> bytes:
    buf = io.BytesIO()
    ext = os.path.splitext(name)[1].lower()
    if ext == ".bmp":
        image.convert("RGB").save(buf, format="BMP")
    elif ext in (".jpg", ".jpeg"):
        image.convert("RGB").save(buf, format="JPEG", quality=93, subsampling=0)
    else:
        image.save(buf, format="PNG")
    return buf.getvalue()


def make_dropin_zip(paks: dict[str, bytes], out_zip: str) -> None:
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as z:
        for rel, blob in paks.items():
            z.writestr(rel, blob)
    print("drop-in zip: %s (%.1f MB)" % (out_zip, os.path.getsize(out_zip) / 1e6))


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", required=True, help="game installation folder (contains Poolians.exe)")
    ap.add_argument("--out", default="build", help="output folder for the rebuilt paks")
    ap.add_argument("--install", action="store_true", help="copy the result into the game (creates .backup)")
    ap.add_argument("--zip", action="store_true", help="also emit a drop-in zip")
    ap.add_argument("--keep-source", action="store_true",
                    help="always read <pak>.backup when it exists (default: on with --install)")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore <pak>.backup files and read the live (possibly modded) pak")
    args = ap.parse_args(argv)

    if not os.path.isfile(os.path.join(args.game, "Poolians.exe")):
        print("!! Poolians.exe not found in", args.game)
        return 2
    os.makedirs(args.out, exist_ok=True)

    built: dict[str, bytes] = {}
    for game in GAMES:
        cue_src = None
        for pak in PAKS:
            live = os.path.join(args.game, game, "3d", pak)
            if not os.path.isfile(live):
                print("!! missing", live)
                continue
            src = live if args.fresh else pristine_source(live)
            if src != live:
                print("    source: pristine copy", os.path.basename(src))

            if game == "RealPool3D" and pak == "common.pak" and cue_src is None:
                with pakcodec.open_pak(src) as zf:
                    from PIL import Image
                    cue_src = Image.open(io.BytesIO(zf.read("ball0.bmp")))

            blob, n, stats = process_pak(game, src, cue_src, game == "RealPool3D")
            rel = "%s/3d/%s" % (game, pak)
            # the drop-in package must contain the *encoded* (XOR 0x78) bytes,
            # exactly what the game expects on disk
            built[rel] = pakcodec.encode(blob)
            target = os.path.join(args.out, game, "3d", pak)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            pakcodec.write_pak(target, blob)
            print("%-30s replaced %3d  (tex %d / ball %d / mat %d)  %.1f MB"
                  % (rel, n, stats["texture"], stats["ball"], stats["material"],
                     os.path.getsize(target) / 1e6))

            if args.install:
                if not any(os.path.isfile(live + s) for s in BACKUP_SUFFIXES):
                    shutil.copy2(live, live + ".backup")
                    print("    backup  ->", live + ".backup")
                pakcodec.write_pak(live, blob)
                print("    installed ->", live)

    if args.zip:
        make_dropin_zip(built, os.path.join(args.out, "Poolians_HD_Mod.zip"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
