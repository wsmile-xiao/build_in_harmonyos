#!/usr/bin/env python3
"""Generate a minimal but valid TrueType font for cube2font smoke tests.

cube2font loads every character of the Cube engine printable charset through
FreeType (FT_Load_Char) and aborts on the first character that is missing from
the font, so the test font must expose a cmap covering the whole charset used
by src/shared/cube2font.c (Latin-1, Latin Extended-A and Cyrillic ranges), not
just ASCII.

The font is built from scratch (no binary blob is stored in the repository):
  * glyph 0  — .notdef, empty outline
  * glyph 1  — empty glyph, kept so the font has the conventional first pair
  * glyph 2  — real rectangular outline, reached by *every* mapped code point

Mapping every code point to the outlined glyph matters: with blank glyphs the
upstream texture packer ends up with an empty row and writes no texture page at
all (`... 0 texs`), so the conversion would silently produce no PNG output.

Usage: python3 make_test_font.py <output.ttf>
"""

import struct
import sys

# Code points requested by cube2font for the Cube engine printable charset
# (src/shared/cube2font.c: cube2unichars[] filtered by iscubeprint()).
CUBE_UNICODES = [
    192, 193, 194, 195, 196, 197, 198, 199, 200, 201,
    202, 203, 204, 205, 206, 207, 209, 210, 211, 212, 213, 214, 216, 217, 218, 219,
    32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
    48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
    64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
    96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
    112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 220,
    221, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237,
    238, 239, 241, 242, 243, 244, 245, 246, 248, 249, 250, 251, 252, 253, 255, 0x104,
    0x105, 0x106, 0x107, 0x10C, 0x10D, 0x10E, 0x10F, 0x118, 0x119, 0x11A, 0x11B,
    0x11E, 0x11F, 0x130, 0x131, 0x141,
    0x142, 0x143, 0x144, 0x147, 0x148, 0x150, 0x151, 0x152, 0x153, 0x158, 0x159,
    0x15A, 0x15B, 0x15E, 0x15F, 0x160,
    0x161, 0x164, 0x165, 0x16E, 0x16F, 0x170, 0x171, 0x178, 0x179, 0x17A, 0x17B,
    0x17C, 0x17D, 0x17E, 0x404, 0x411,
    0x413, 0x414, 0x416, 0x417, 0x418, 0x419, 0x41B, 0x41F, 0x423, 0x424, 0x426,
    0x427, 0x428, 0x429, 0x42A, 0x42B,
    0x42C, 0x42D, 0x42E, 0x42F, 0x431, 0x432, 0x433, 0x434, 0x436, 0x437, 0x438,
    0x439, 0x43A, 0x43B, 0x43C, 0x43D,
    0x43F, 0x442, 0x444, 0x446, 0x447, 0x448, 0x449, 0x44A, 0x44B, 0x44C, 0x44D,
    0x44E, 0x44F, 0x454, 0x490, 0x491,
]

UPM = 1024
GLYPH_A = 2                       # glyph index carrying the real outline
ADVANCE = 512
NOTDEF_ADVANCE = 512


def _pad4(data):
    return data + b"\0" * ((4 - len(data) % 4) % 4)


def _checksum(data):
    data = _pad4(data)
    return sum(struct.unpack(">%dI" % (len(data) // 4), data)) & 0xFFFFFFFF


def _simple_glyph(pts):
    """Build a single-contour simple glyph; pts are on-curve absolute points."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    out = struct.pack(">hhhhh", 1, min(xs), min(ys), max(xs), max(ys))
    out += struct.pack(">H", len(pts) - 1)          # endPtsOfContours
    out += struct.pack(">H", 0)                     # instructionLength
    out += bytes([0x01] * len(pts))                 # on-curve, int16 deltas
    dx, dy = 0, 0
    for x, _ in pts:
        out += struct.pack(">h", x - dx)
        dx = x
    for _, y in pts:
        out += struct.pack(">h", y - dy)
        dy = y
    return out


def _segments(codepoints):
    segs = []
    for cp in sorted(set(codepoints)):
        if segs and cp == segs[-1][1] + 1:
            segs[-1][1] = cp
        else:
            segs.append([cp, cp])
    return segs


def _build_cmap(codepoints):
    # Format 4 idDelta is a constant offset per segment, and idRangeOffset
    # arrays would be needed to fold a whole range onto one glyph, so use one
    # segment per code point (250 segments, ~2 KB): every code point resolves
    # to the outlined glyph through its own delta.
    segs = [[c, c] for c in sorted(set(codepoints))]
    segs.append([0xFFFF, 0xFFFF])
    seg_count = len(segs)
    end_codes, start_codes, deltas = [], [], []
    for start, end in segs:
        start_codes.append(start)
        end_codes.append(end)
        if start == 0xFFFF:
            deltas.append(1)
        else:
            deltas.append((GLYPH_A - start) & 0xFFFF)
    search = 2 * (2 ** (seg_count.bit_length() - 1))
    entry_selector = search.bit_length() - 2
    sub = struct.pack(">HHHHHHH", 4, 0, 0, seg_count * 2, search,
                      entry_selector, seg_count * 2 - search)
    sub += b"".join(struct.pack(">H", c) for c in end_codes)
    sub += struct.pack(">H", 0)
    sub += b"".join(struct.pack(">H", c) for c in start_codes)
    sub += b"".join(struct.pack(">H", d) for d in deltas)
    sub += b"".join(struct.pack(">H", 0) for _ in segs)   # idRangeOffset
    sub = struct.pack(">HHH", 4, len(sub), 0) + sub[6:]
    cmap = struct.pack(">HH", 0, 1)
    cmap += struct.pack(">HHI", 3, 1, 12)
    cmap += sub
    return cmap


def _build_name():
    strings = {1: "cube2font Test Font", 2: "Regular"}
    records, storage = b"", b""
    for name_id in sorted(strings):
        raw = strings[name_id].encode("utf-16-be")
        records += struct.pack(">HHHHHH", 3, 1, 0x409, name_id, len(raw),
                               len(storage))
        storage += raw
    header = struct.pack(">HHH", 0, len(strings), 6 + 12 * len(strings))
    return header + records + storage


def build_font(codepoints):
    glyf = b""                       # glyph 0: .notdef (empty)
    glyf += b""                      # glyph 1: blank glyph (empty)
    glyf += _simple_glyph([(100, 0), (500, 0), (500, 700), (100, 700)])
    loca = [0, 0, 0, len(glyf)]

    loca_tbl = b"".join(struct.pack(">H", off // 2) for off in loca)
    hmtx = struct.pack(">Hh", NOTDEF_ADVANCE, 0)
    hmtx += struct.pack(">Hh", ADVANCE, 0)
    hmtx += struct.pack(">Hh", ADVANCE, 100)

    maxp = struct.pack(">IHHHHHHHHHHHHHH", 0x00010000, 3, 4, 1, 0, 0, 2, 0, 0, 0,
                       0, 0, 0, 0, 0)
    hhea = struct.pack(">IhhhHhhhhhhhhhhhH", 0x00010000, 800, -200, 0, ADVANCE,
                       100, 0, 500, 1, 0, 0, 0, 0, 0, 0, 0, 3)
    post = struct.pack(">IIhhIIIII", 0x00030000, 0, 0, 0, 0, 0, 0, 0, 0)

    tables = {
        "cmap": _build_cmap(codepoints),
        "glyf": glyf,
        "hhea": hhea,
        "hmtx": hmtx,
        "loca": loca_tbl,
        "maxp": maxp,
        "name": _build_name(),
        "post": post,
    }
    # head is built last: it embeds the file-wide checksum adjustment.
    tags = sorted(list(tables) + ["head"])
    num_tables = len(tags)
    search = 16 * (2 ** (num_tables.bit_length() - 1))
    entry_selector = search.bit_length() - 5
    header = struct.pack(">IHHHH", 0x00010000, num_tables, search,
                         entry_selector, num_tables * 16 - search)

    offset = len(header) + 16 * num_tables
    directory, body, body_offset = b"", b"", {}
    for tag in tags:
        data = tables[tag] if tag != "head" else b"\0" * 54
        directory += struct.pack(">4sIII", tag.encode("ascii"),
                                 _checksum(data) if tag != "head" else 0,
                                 offset, len(data))
        body_offset[tag] = offset
        body += _pad4(data)
        offset += len(_pad4(data))

    head_offset = body_offset["head"]
    head = struct.pack(">IIIIHHqqhhhhHHhhh", 0x00010000, 0x00010000, 0,
                       0x5F0F3CF5, 0x0003, UPM, 0, 0, 0, 0, 500, 700, 0, 8, 2,
                       0, 0)
    assert len(head) == 54, len(head)

    font = bytearray(header + directory + body)
    font[head_offset:head_offset + 54] = head
    # head checksum over the zeroed-checkSumAdjustment head
    dir_off = len(header) + 16 * tags.index("head")
    font[dir_off + 4:dir_off + 8] = struct.pack(">I", _checksum(bytes(head)))
    adjustment = (0xB1B0AFBA - _checksum(bytes(font))) & 0xFFFFFFFF
    font[head_offset + 8:head_offset + 12] = struct.pack(">I", adjustment)
    return bytes(font)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: make_test_font.py <output.ttf>")
    data = build_font(CUBE_UNICODES)
    with open(sys.argv[1], "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes, %d mapped code points)"
          % (sys.argv[1], len(data), len(set(CUBE_UNICODES))))


if __name__ == "__main__":
    main()
