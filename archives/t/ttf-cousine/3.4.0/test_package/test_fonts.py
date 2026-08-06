#!/usr/bin/env python3
"""Validate packaged Cousine Nerd Font TTF files."""

import glob
import os
import struct
import sys


VALID_MAGIC = (0x00010000, 0x74727565, 0x4F54544F)


def main(argv):
    if not argv:
        raise SystemExit("usage: test_fonts.py <font-dir> [<font-dir>...]")

    ttf_files = []
    for font_dir in argv:
        if not os.path.isdir(font_dir):
            raise SystemExit(f"font directory not found: {font_dir}")
        ttf_files.extend(sorted(glob.glob(os.path.join(font_dir, "*.ttf"))))

    if len(ttf_files) < 12:
        raise SystemExit(f"expected at least 12 TTF files, found {len(ttf_files)}")

    for ttf_path in ttf_files:
        size = os.path.getsize(ttf_path)
        if size < 12:
            raise SystemExit(f"{os.path.basename(ttf_path)} too small: {size} bytes")
        with open(ttf_path, "rb") as font_file:
            magic = struct.unpack(">I", font_file.read(4))[0]
        if magic not in VALID_MAGIC:
            raise SystemExit(
                f"{os.path.basename(ttf_path)} invalid magic 0x{magic:08X}"
            )

    print(f"OK: {len(ttf_files)} TTF files validated")


if __name__ == "__main__":
    main(sys.argv[1:])
