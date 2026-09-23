#!/usr/bin/env python3
"""Assertions on the font assets cube2font actually produced.

Usage: check_output.py <name.cfg> <expected-chars> [--exact]

Everything is derived from the produced .cfg / .png pair, so the checks scale
with the font that was converted (page count, character metrics):

  * the .cfg starts with the echoed argv comment, declares the font and names
    every texture page it references; the referenced PNG files must exist
  * the .cfg lists exactly <expected-chars> `fontchar` entries, each with a
    non-empty bitmap that fits inside its texture page
  * every PNG page carries a valid signature, a valid CRC per chunk and an IDAT
    stream that inflates to exactly height * (width * 2 + 1) bytes (8-bit
    greyscale+alpha rows, one filter byte per row)
  * every non-zero pixel of every page falls inside the rectangle the .cfg
    reports for a character (the atlas and the coordinate table agree)
  * with --exact the non-zero pixels must fill those rectangles exactly, which
    holds for the unstroked conversion; a stroked conversion rounds its corners
    and is therefore only checked as a subset

The number of assertions actually performed is printed so the reported test
counts can be recomputed from the log.
"""

import re
import struct
import sys
import zlib

_checks = [0]


def check(ok, message):
    _checks[0] += 1
    if not ok:
        print("FAIL: %s" % message)
        sys.exit(1)


def fail(message):
    print("FAIL: %s" % message)
    sys.exit(1)


def quoted(line):
    return re.findall(r'"([^"]*)"', line)


def strip_grey(name):
    return name[len("<grey>"):] if name.startswith("<grey>") else name


def page_index(filename):
    match = re.search(r"(\d+)\.png$", filename)
    if not match:
        fail("cannot derive the texture page number from %r" % filename)
    return int(match.group(1))


def parse_cfg(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    if not lines or not lines[0].startswith("//"):
        fail("%s: first line is not the echoed command line" % path)

    pages, chars, current = {}, [], None
    for line in lines:
        if line.startswith("font "):
            names = quoted(line)
            if len(names) < 2:
                fail("%s: malformed font declaration: %s" % (path, line))
            current = page_index(strip_grey(names[1]))
            pages[current] = strip_grey(names[1])
        elif line.startswith("fonttex "):
            names = quoted(line)
            if not names:
                fail("%s: malformed fonttex line: %s" % (path, line))
            current = page_index(strip_grey(names[0]))
            pages[current] = strip_grey(names[0])
        elif line.startswith("fontchar "):
            if current is None:
                fail("%s: fontchar before any texture page: %s" % (path, line))
            nums = [int(t) for t in line.split("//")[0].split()[1:8]]
            if len(nums) != 7:
                fail("%s: malformed fontchar line: %s" % (path, line))
            # trailing comment is "(<code>)" or "(<code> -> 0x<unicode>)"
            code = int(line.split("(")[-1].rstrip(")").split()[0])
            chars.append((current, nums, code))
    if not pages:
        fail("%s: no texture page declared" % path)
    return pages, chars


def read_png(path):
    data = open(path, "rb").read()
    check(data[:8] == b"\x89PNG\r\n\x1a\n", "%s: missing PNG signature" % path)
    off, idat, ihdr, chunks, crc_ok = 8, b"", None, [], True
    while off < len(data):
        if off + 8 > len(data):
            fail("%s: truncated chunk header" % path)
        length, ctype = struct.unpack(">I4s", data[off:off + 8])
        off += 8
        payload = data[off:off + length]
        off += length
        crc = struct.unpack(">I", data[off:off + 4])[0]
        off += 4
        if crc != zlib.crc32(ctype + payload) & 0xFFFFFFFF:
            crc_ok = False
        chunks.append(ctype)
        if ctype == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif ctype == b"IDAT":
            idat += payload
    check(crc_ok, "%s: bad chunk CRC" % path)
    check(ihdr is not None and b"IEND" in chunks,
          "%s: incomplete PNG (chunks=%s)"
          % (path, [c.decode("ascii", "replace") for c in chunks]))
    width, height, depth, color, _, _, _ = ihdr
    check((depth, color) == (8, 4),
          "%s: expected 8-bit greyscale+alpha, got depth=%d color=%d"
          % (path, depth, color))
    raw = zlib.decompress(idat)
    check(len(raw) == height * (width * 2 + 1),
          "%s: IDAT inflates to %d bytes, expected %d"
          % (path, len(raw), height * (width * 2 + 1)))
    stride = width * 2
    rows = [raw[i * (stride + 1) + 1:(i + 1) * (stride + 1)] for i in range(height)]
    ink = {(x, y) for y in range(height) for x in range(width)
           if rows[y][2 * x] or rows[y][2 * x + 1]}
    return width, height, ink


def main():
    exact = "--exact" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    cfg_path, expected = args[0], int(args[1])

    pages, chars = parse_cfg(cfg_path)
    check(len(chars) == expected,
          "%s: %d fontchar entries, expected %d" % (cfg_path, len(chars), expected))
    empty = [n for n in (nums[:4] for _, nums, _ in chars) if n[2] <= 0 or n[3] <= 0]
    check(not empty,
          "%s: %d character(s) reported an empty bitmap, first %s"
          % (cfg_path, len(empty), empty[:1]))

    boxes = {}
    for page, nums, _code in chars:
        boxes.setdefault(page, []).append(tuple(nums[:4]))

    total_ink, total_area = 0, 0
    for page in sorted(pages):
        check(page in boxes,
              "%s: texture page %d is declared but holds no character" % (cfg_path, page))
        path = pages[page]
        width, height, ink = read_png(path)
        area = set()
        for x, y, w, h in boxes[page]:
            area |= {(cx, cy) for cy in range(y, y + h) for cx in range(x, x + w)}
        escaped = [b for b in boxes[page]
                   if b[0] < 0 or b[1] < 0 or b[0] + b[2] > width or b[1] + b[3] > height]
        check(not escaped,
              "%s: character box %s escapes the %dx%d texture page"
              % (path, escaped[:1], width, height))
        stray = ink - area
        check(not stray,
              "%s: %d non-zero pixels outside every character box (e.g. %s)"
              % (path, len(stray), sorted(stray)[:3]))
        if exact:
            check(ink == area,
                  "%s: %d of the %d boxed pixels carry no ink"
                  % (path, len(area) - len(ink), len(area)))
        total_ink += len(ink)
        total_area += len(area)
        print("OK: %s %dx%d, %d characters, %d/%d boxed pixels inked"
              % (path, width, height, len(boxes[page]), len(ink), len(area)))

    print("OK: %s — %d characters over %d texture page(s), %d/%d boxed pixels inked%s"
          % (cfg_path, len(chars), len(pages), total_ink, total_area,
             " (exact)" if exact else ""))
    print("ASSERTIONS: %d" % _checks[0])


if __name__ == "__main__":
    main()
