#!/usr/bin/env python3
"""Generate a minimal valid Doom-format WAD (MAP01) as test input for zdbsp.

One map with 2 vertices, 1 linedef, 1 sidedef, 1 sector — 186 bytes total.
zdbsp builds BSP nodes for it (adds SEGS/SSECTORS/BLOCKMAP lumps) and exits 0.

This generator exists as a text file (not a committed binary) so the PR diff
stays text-only and applies cleanly in CI (git apply cannot apply binary
patches served by GitCode .diff).
"""
import struct
import sys


def build_wad(lumps):
    data = b""
    entries = []
    for name, blob in lumps:
        offset = 12 + len(data)
        entries.append((offset, len(blob), name))
        data += blob
    header = b"PWAD" + struct.pack("<II", len(lumps), 12 + len(data))
    directory = b""
    for offset, size, name in entries:
        directory += struct.pack("<II", offset, size) + name.encode().ljust(8, b"\0")[:8]
    return header + data + directory


def main():
    vertices = struct.pack("<hhhh", 0, 0, 64, 0)
    linedefs = struct.pack("<hhhhhhh", 0, 1, 0, 0, 0, 0, -1)
    sidedefs = struct.pack("<hh8s8s8sh", 0, 0, b"TEX1", b"TEX1", b"TEX1", 0)
    sectors = struct.pack("<hh8s8shhh", 0, 128, b"FLOOR1", b"CEIL1", 160, 0, 0)
    sys.stdout.buffer.write(build_wad([
        ("MAP01", b""),
        ("THINGS", b""),
        ("LINEDEFS", linedefs),
        ("SIDEDEFS", sidedefs),
        ("VERTEXES", vertices),
        ("SECTORS", sectors),
    ]))


if __name__ == "__main__":
    main()
