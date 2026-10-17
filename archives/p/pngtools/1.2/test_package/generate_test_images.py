#!/usr/bin/env python3
"""Generate the PNG fixtures required by the upstream tests.

This is a standard-library equivalent of the upstream Pillow-based fixture
generator.  It produces the same image dimensions, colour models and chunks.
"""

import argparse
import os
import struct
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunk(kind, payload):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def write_png(
    path, width, height, bit_depth, colour_type, rows, extras=(), interlace=0
):
    ihdr = struct.pack(
        ">IIBBBBB", width, height, bit_depth, colour_type, 0, 0, interlace
    )
    raw = b"".join(b"\x00" + row for row in rows)
    data = [chunk(b"IHDR", ihdr)]
    data.extend(chunk(kind, payload) for kind, payload in extras)
    data.append(chunk(b"IDAT", zlib.compress(raw)))
    data.append(chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(PNG_SIGNATURE + b"".join(data))


def palette_rows(width, height):
    return [bytes((x + y) % 4 for x in range(width)) for y in range(height)]


def generate_paletted(output_dir):
    palette = bytes((255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0))
    write_png(
        os.path.join(output_dir, "paletted.png"),
        32,
        32,
        8,
        3,
        palette_rows(32, 32),
        extras=[(b"PLTE", palette)],
    )


def interlaced_rows(width, height):
    """Build valid Adam7 scanlines for RGB8 data."""
    passes = (
        (0, 0, 8, 8),
        (4, 0, 8, 8),
        (0, 4, 4, 8),
        (2, 0, 4, 4),
        (0, 2, 2, 4),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    )
    rows = []
    for x_start, y_start, x_step, y_step in passes:
        if width <= x_start or height <= y_start:
            continue
        pass_width = (width - x_start + x_step - 1) // x_step
        pass_height = (height - y_start + y_step - 1) // y_step
        for pass_y in range(pass_height):
            y = y_start + pass_y * y_step
            row = bytearray()
            for pass_x in range(pass_width):
                x = x_start + pass_x * x_step
                row.extend(((x * 8) & 0xFF, (y * 8) & 0xFF, 128))
            rows.append(bytes(row))
    return rows


def generate_interlaced(output_dir):
    write_png(
        os.path.join(output_dir, "interlaced.png"),
        32,
        32,
        8,
        2,
        interlaced_rows(32, 32),
        interlace=1,
    )


def generate_with_text(output_dir):
    rows = [bytes((100, 150, 200)) * 32 for _ in range(32)]
    write_png(
        os.path.join(output_dir, "with_text.png"),
        32,
        32,
        8,
        2,
        rows,
        extras=[
            (b"tEXt", b"Author\x00pngtools test suite"),
            (b"tEXt", b"Description\x00Test image with text chunks"),
        ],
    )


def generate_with_transparency(output_dir):
    palette = bytes((255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0))
    write_png(
        os.path.join(output_dir, "with_transparency.png"),
        32,
        32,
        8,
        3,
        palette_rows(32, 32),
        extras=[(b"PLTE", palette), (b"tRNS", b"\x00")],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)
    generate_paletted(args.output)
    generate_interlaced(args.output)
    generate_with_text(args.output)
    generate_with_transparency(args.output)
    print("generated testdata in %s" % args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
