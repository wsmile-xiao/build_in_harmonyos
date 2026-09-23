#!/usr/bin/env python3
"""Generate a minimal tiled RGB TIFF that OpenSlide detects as generic-tiff.

Pure stdlib (no numpy/tifffile) so it can run inside the Conan/CI environment.
OpenSlide's generic-tiff vendor requires the first TIFF directory to be tiled
(TileWidth/TileLength present) - see src/openslide-vendor-generic-tiff.c.
"""
import struct
import sys

W = H = 256          # image size (pixels)
TW = TH = 128        # tile size (libtiff requires a multiple of 16)
SPP = 3              # RGB

TILES_X = (W + TW - 1) // TW
TILES_Y = (H + TH - 1) // TH
NTILES = TILES_X * TILES_Y
TILE_BYTES = TW * TH * SPP


def tile_bytes(tx, ty):
    out = bytearray(TW * TH * SPP)
    for y in range(TH):
        gy = ty * TH + y
        base = y * TW * SPP
        for x in range(TW):
            gx = tx * TW + x
            o = base + x * SPP
            out[o] = gx & 0xFF          # R: horizontal ramp
            out[o + 1] = gy & 0xFF      # G: vertical ramp
            out[o + 2] = 0x80           # B: constant
    return bytes(out)


def main(path):
    # offsets of the SHORT/RATIONAL/array payloads stored after the IFD
    ifd_offset = 8
    n_entries = 15
    extra_offset = ifd_offset + 2 + n_entries * 12 + 4

    bps_off = extra_offset
    xres_off = bps_off + 2 * SPP
    yres_off = xres_off + 8
    sfmt_off = yres_off + 8
    offsets_off = sfmt_off + 2 * SPP
    counts_off = offsets_off + 4 * NTILES
    data_off = counts_off + 4 * NTILES

    tile_offsets = [data_off + i * TILE_BYTES for i in range(NTILES)]
    tile_counts = [TILE_BYTES] * NTILES

    out = bytearray()
    out += b"II" + struct.pack("<HI", 42, ifd_offset)
    out += struct.pack("<H", n_entries)

    def entry(tag, typ, cnt, val):
        # TIFF entry: tag(u16) type(u16) count(u32) value(u32); SHORT values are
        # stored in the first two bytes of the value field.
        if typ == 3 and cnt == 1:
            out.extend(struct.pack("<HHIHH", tag, typ, cnt, val, 0))
        else:
            out.extend(struct.pack("<HHII", tag, typ, cnt, val))

    entry(256, 4, 1, W)                 # ImageWidth (LONG)
    entry(257, 4, 1, H)                 # ImageLength (LONG)
    entry(258, 3, SPP, bps_off)         # BitsPerSample (SHORT x3)
    entry(259, 3, 1, 1)                 # Compression = none
    entry(262, 3, 1, 2)                 # Photometric = RGB
    entry(277, 3, 1, SPP)               # SamplesPerPixel
    entry(282, 5, 1, xres_off)          # XResolution (RATIONAL)
    entry(283, 5, 1, yres_off)          # YResolution (RATIONAL)
    entry(284, 3, 1, 1)                 # PlanarConfiguration = contiguous
    entry(296, 3, 1, 2)                 # ResolutionUnit = inch
    entry(322, 4, 1, TW)                # TileWidth (LONG)
    entry(323, 4, 1, TH)                # TileLength (LONG)
    entry(324, 4, NTILES, offsets_off)  # TileOffsets (LONG xN)
    entry(325, 4, NTILES, counts_off)   # TileByteCounts (LONG xN)
    entry(339, 3, SPP, sfmt_off)        # SampleFormat (SHORT x3)

    out += struct.pack("<I", 0)         # next IFD = none

    assert len(out) == extra_offset, (len(out), extra_offset)
    out += struct.pack("<" + "H" * SPP, *([8] * SPP))          # BitsPerSample
    out += struct.pack("<II", 72, 1)                           # XResolution
    out += struct.pack("<II", 72, 1)                           # YResolution
    out += struct.pack("<" + "H" * SPP, *([1] * SPP))          # SampleFormat
    out += b"".join(struct.pack("<I", o) for o in tile_offsets)
    out += b"".join(struct.pack("<I", c) for c in tile_counts)

    assert len(out) == data_off, (len(out), data_off)
    for ty in range(TILES_Y):
        for tx in range(TILES_X):
            out += tile_bytes(tx, ty)

    with open(path, "wb") as fh:
        fh.write(out)
    print("wrote %s (%d bytes, %d tiles of %dx%d)" %
          (path, len(out), NTILES, TW, TH))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "synthetic-generic-tiff.tif")
