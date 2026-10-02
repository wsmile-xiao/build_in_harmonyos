#!/usr/bin/env python3
"""gen_images.py - materialise metapixel's test inputs at test time.

Why this exists instead of shipping image files in the repository:
the CI worker checks out a PR by downloading a *text* diff
(https://<host>/pull/<n>.diff) and applying it with `git apply`.  That
endpoint carries no binary payload, so any committed .png/.jpg/.gif makes
the whole PR fail at the `checkout-pr` step with
"error: missing binary patch data for ...".  Everything in this recipe must
therefore stay text, and the test images are generated instead.

PNG and GIF are written from scratch here with nothing but the standard
library, so the fixtures are fully auditable - you can read exactly what the
decoder under test is being fed.  The JPEG fixture is the one format that is
not worth a hand-written encoder, so it is embedded as base64 together with
its SHA256; `check()` verifies the digest before the image is used, so the
constant cannot silently drift.

usage: python3 gen_images.py <output-dir>
exits non-zero if the output directory is unusable
"""
import base64
import binascii
import hashlib
import os
import struct
import sys
import zlib

# --------------------------------------------------------------------------
# PNG (8-bit truecolour, no interlacing)
# --------------------------------------------------------------------------


def _png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, width, height, pixel):
    """pixel(x, y) -> (r, g, b).  Filter type 0 on every scanline."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)                      # filter type: None
        for x in range(width):
            raw.extend(pixel(x, y))
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                                           8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


# --------------------------------------------------------------------------
# GIF (GIF89a, global colour table, LZW)
# --------------------------------------------------------------------------


def _lzw(indices, min_code_size):
    """Minimal GIF LZW encoder; codes are packed least-significant bit first."""
    clear = 1 << min_code_size
    end = clear + 1
    out = bytearray()
    acc = 0
    nbits = 0

    def emit(code, width):
        nonlocal acc, nbits
        acc |= code << nbits
        nbits += width
        while nbits >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            nbits -= 8

    table = {bytes([i]): i for i in range(clear)}
    nxt = end + 1
    width = min_code_size + 1
    emit(clear, width)

    run = b""
    for value in indices:
        grown = run + bytes([value])
        if grown in table:
            run = grown
            continue
        emit(table[run], width)
        table[grown] = nxt
        nxt += 1
        # A code width bump must never skip 2**width, or the decoder desyncs.
        if nxt > (1 << width) and width < 12:
            width += 1
        if nxt >= 4095:
            emit(clear, width)
            table = {bytes([i]): i for i in range(clear)}
            nxt = end + 1
            width = min_code_size + 1
        run = bytes([value])
    if run:
        emit(table[run], width)
    emit(end, width)
    if nbits:
        out.append(acc & 0xFF)
    return bytes(out)


def _gif_subblocks(data):
    out = bytearray()
    for start in range(0, len(data), 255):
        piece = data[start:start + 255]
        out.append(len(piece))
        out.extend(piece)
    out.append(0)                            # block terminator
    return bytes(out)


def write_gif(path, width, height, pixel, palette):
    """palette: list of (r, g, b), 2..256 entries.  pixel(x, y) -> palette index."""
    depth = max(1, (len(palette) - 1).bit_length())
    table_size = 1 << depth
    gif = b"GIF89a"
    # Logical Screen Descriptor: global colour table present, size 2**depth
    gif += struct.pack("<HHBBB", width, height, 0x80 | ((depth - 1) << 4) | (depth - 1),
                       0, 0)
    table = bytearray()
    for entry in palette:
        table.extend(entry)
    table.extend(b"\x00\x00\x00" * (table_size - len(palette)))
    gif += bytes(table)
    # Image Descriptor (no local colour table, not interlaced)
    gif += b"\x2C" + struct.pack("<HHHHB", 0, 0, width, height, 0x00)
    min_code_size = max(2, depth)
    gif += bytes([min_code_size])
    indices = [pixel(x, y) for y in range(height) for x in range(width)]
    gif += _gif_subblocks(_lzw(indices, min_code_size))
    gif += b"\x3B"                           # trailer
    with open(path, "wb") as handle:
        handle.write(gif)


# --------------------------------------------------------------------------
# JPEG fixture (base64; encoder not worth hand-writing)
# --------------------------------------------------------------------------

TILE_C_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsK"
    "CwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQU"
    "FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAAQABADASIA"
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
    "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
    "U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
    "uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD518If"
    "CThP3P6V7Z4R+EnKfuf0r2jwh8JOU/c/pXtvhH4Sfc/c/pX7PnXGe/vHneGPiD/D9/sf/9k="
)
TILE_C_JPEG_SHA256 = "ad43b835d9c6056aa496935a72bb9d7a3db909997250145f8d7b919329981da1"


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


def build(target_dir):
    os.makedirs(target_dir, exist_ok=True)

    # 64x64 target: a smooth RGB ramp.  A gradient gives the matcher real work
    # to do, and the size is a multiple of the 8x8 tile grid so the mosaic
    # comes out exactly 64x64 (asserted by the test).
    write_png(os.path.join(target_dir, "target.png"), 64, 64,
              lambda x, y: (x * 4, y * 4, 128))

    # Two PNG tiles.
    write_png(os.path.join(target_dir, "tile_a.png"), 16, 16,
              lambda x, y: (x * 16, y * 16, 40))
    write_png(os.path.join(target_dir, "tile_b.png"), 16, 16,
              lambda x, y: (x * 16, y * 16, 200))

    # One GIF tile: exercises the giflib backend that patch 0001 fixes.
    # 16-colour palette, index = (x + y) % 16, deliberately not a flat block
    # so the LZW stream really varies.
    palette = [(i * 16, (255 - i * 16), (i * 8) % 256) for i in range(16)]
    write_gif(os.path.join(target_dir, "tile_c.gif"), 16, 16,
              lambda x, y: (x + y) % 16, palette)

    # One JPEG tile, decoded from the embedded base64 constant.
    jpeg = base64.b64decode(TILE_C_JPEG_B64)
    digest = hashlib.sha256(jpeg).hexdigest()
    if digest != TILE_C_JPEG_SHA256:
        raise SystemExit(
            "embedded JPEG fixture digest mismatch: got %s, expected %s"
            % (digest, TILE_C_JPEG_SHA256))
    with open(os.path.join(target_dir, "tile_d.jpg"), "wb") as handle:
        handle.write(jpeg)
    return sorted(os.listdir(target_dir))


def check(target_dir):
    """Cheap structural verification so a broken generator cannot fake a pass."""
    expect = {
        "target.png": b"\x89PNG\r\n\x1a\n",
        "tile_a.png": b"\x89PNG\r\n\x1a\n",
        "tile_b.png": b"\x89PNG\r\n\x1a\n",
        "tile_c.gif": b"GIF89a",
        "tile_d.jpg": b"\xff\xd8\xff",
    }
    for name, magic in expect.items():
        path = os.path.join(target_dir, name)
        if not os.path.isfile(path):
            raise SystemExit("gen_images: missing %s" % path)
        size = os.path.getsize(path)
        if size < 64:
            raise SystemExit("gen_images: %s suspiciously small (%d bytes)" % (name, size))
        with open(path, "rb") as handle:
            head = handle.read(len(magic))
        if head != magic:
            raise SystemExit("gen_images: %s bad magic %r (want %r)" % (name, head, magic))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__)
        raise SystemExit(2)
    out = sys.argv[1]
    names = build(out)
    check(out)
    sys.stdout.write("gen_images: %d fixtures in %s\n" % (len(names), out))
    for name in names:
        path = os.path.join(out, name)
        sys.stdout.write("  %-12s %6d bytes  %s\n"
                         % (name, os.path.getsize(path),
                            hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]))
