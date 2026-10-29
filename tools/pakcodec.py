"""Poolians ``.pak`` archive codec.

The game's ``.pak`` files are plain ZIP archives with every byte XOR-ed with
``0x78``.  Ogre's archive factory registers them under the type name "pak"
(see ``docs/pak-format.md`` for the evidence).

This module is intentionally dependency-free so it can be used as a library::

    from pakcodec import open_pak, repack

    for info in open_pak(r"...\\RealPool3D\\3d\\common.pak").infolist():
        print(info.filename, info.file_size)
"""
from __future__ import annotations

import io
import os
import zipfile

KEY = 0x78


def decode(data: bytes) -> bytes:
    """XOR every byte with 0x78, turning a ``.pak`` blob into a ZIP blob."""
    return bytes(b ^ KEY for b in data)


def encode(data: bytes) -> bytes:
    """Inverse of :func:`decode` - ZIP blob back into a ``.pak`` blob."""
    return bytes(b ^ KEY for b in data)


def read_pak(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def write_pak(path: str, blob: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(encode(blob))


def open_pak(path: str) -> zipfile.ZipFile:
    """Open a ``.pak`` file as a read-only :class:`zipfile.ZipFile`."""
    return zipfile.ZipFile(io.BytesIO(decode(read_pak(path))))


def extract(path: str, out_dir: str, pattern: str = "") -> list[str]:
    """Extract entries whose name contains *pattern* (case-insensitive)."""
    names = []
    pat = pattern.lower()
    with open_pak(path) as zf:
        for info in zf.infolist():
            if pat and pat not in info.filename.lower():
                continue
            target = os.path.join(out_dir, info.filename.replace("/", os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as fh:
                fh.write(zf.read(info.filename))
            names.append(info.filename)
    return names


def repack(src_pak: str, out_pak: str, overrides_dir: str) -> tuple[int, int]:
    """Rebuild *src_pak* into *out_pak*, replacing files found in *overrides_dir*.

    Entry order, timestamps and attributes are preserved so the output is
    reproducible.  Returns ``(replaced_count, output_size)``.
    """
    zf = open_pak(src_pak)
    buf = io.BytesIO()
    replaced = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as dst:
        for info in zf.infolist():
            data = zf.read(info.filename)
            candidate = os.path.join(overrides_dir, info.filename)
            if os.path.isfile(candidate):
                with open(candidate, "rb") as fh:
                    data = fh.read()
                replaced += 1
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            dst.writestr(zi, data)
    zf.close()
    blob = buf.getvalue()
    write_pak(out_pak, blob)
    return replaced, os.path.getsize(out_pak)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Inspect or extract a Poolians .pak")
    ap.add_argument("pak", help="path to the .pak file")
    ap.add_argument("-l", "--list", action="store_true", help="list entries")
    ap.add_argument("-x", "--extract", metavar="DIR", help="extract into DIR")
    ap.add_argument("-v", "--verify", action="store_true", help="check the ZIP is readable")
    args = ap.parse_args(argv)

    with open_pak(args.pak) as zf:
        if args.verify:
            bad = zf.testzip()
            print("OK" if bad is None else "CORRUPT at %s" % bad)
        if args.list or not (args.extract or args.verify):
            total = 0
            for info in zf.infolist():
                total += info.file_size
                print("%-28s %8d -> %8d" % (info.filename, info.compress_size, info.file_size))
            print("%d entries, %.1f MB unpacked" % (len(zf.infolist()), total / 1e6))
    if args.extract:
        names = extract(args.pak, args.extract)
        print("extracted %d files to %s" % (len(names), args.extract))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
