#!/usr/bin/env python3
"""Verify Adwaita font files: existence, count, non-empty, TTF magic."""

import os
import struct
import sys


def main():
    # First argument is the package folder
    pkg_folder = sys.argv[1] if len(sys.argv) > 1 else ""
    font_dir = os.path.join(pkg_folder, "share", "fonts", "Adwaita")

    expected = [
        "AdwaitaMono-Bold.ttf",
        "AdwaitaMono-BoldItalic.ttf",
        "AdwaitaMono-Italic.ttf",
        "AdwaitaMono-Regular.ttf",
        "AdwaitaSans-Italic.ttf",
        "AdwaitaSans-Regular.ttf",
    ]

    files = sorted(os.listdir(font_dir))
    assert len(files) == 6, f"Expected 6 font files, got {len(files)}: {files}"

    for fname in expected:
        path = os.path.join(font_dir, fname)
        assert os.path.isfile(path), f"Missing font file: {path}"
        size = os.path.getsize(path)
        assert size > 0, f"Font file is empty: {path}"
        with open(path, "rb") as fp:
            magic = struct.unpack(">I", fp.read(4))[0]
        assert magic == 0x00010000, f"Invalid TTF magic in {fname}: {magic:#010x}"

    print(f"✅ All 6 font files verified in {font_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()