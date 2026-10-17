#!/usr/bin/env python3
"""Verify Source Sans 3 font files: existence, count, non-empty, TTF magic."""

import os
import struct
import sys


def main():
    # First argument is the package folder
    pkg_folder = sys.argv[1] if len(sys.argv) > 1 else ""
    font_dir = os.path.join(pkg_folder, "share", "fonts", "SourceSans3")

    expected = [
        "SourceSans3-Black.ttf",
        "SourceSans3-BlackIt.ttf",
        "SourceSans3-Bold.ttf",
        "SourceSans3-BoldIt.ttf",
        "SourceSans3-ExtraLight.ttf",
        "SourceSans3-ExtraLightIt.ttf",
        "SourceSans3-It.ttf",
        "SourceSans3-Light.ttf",
        "SourceSans3-LightIt.ttf",
        "SourceSans3-Medium.ttf",
        "SourceSans3-MediumIt.ttf",
        "SourceSans3-Regular.ttf",
        "SourceSans3-Semibold.ttf",
        "SourceSans3-SemiboldIt.ttf",
    ]

    files = sorted(os.listdir(font_dir))
    ttf_files = [f for f in files if f.endswith(".ttf")]
    assert len(ttf_files) == 14, f"Expected 14 font files, got {len(ttf_files)}: {ttf_files}"

    for fname in expected:
        path = os.path.join(font_dir, fname)
        assert os.path.isfile(path), f"Missing font file: {path}"
        size = os.path.getsize(path)
        assert size > 0, f"Font file is empty: {path}"
        with open(path, "rb") as fp:
            magic = struct.unpack(">I", fp.read(4))[0]
        assert magic == 0x00010000, f"Invalid TTF magic in {fname}: {magic:#010x}"

    # License file must be installed alongside fonts
    license_path = os.path.join(font_dir, "LICENSE.md")
    assert os.path.isfile(license_path), f"Missing license file: {license_path}"
    assert os.path.getsize(license_path) > 0, f"License file is empty: {license_path}"

    print(f"✅ All 14 font files + LICENSE.md verified in {font_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
