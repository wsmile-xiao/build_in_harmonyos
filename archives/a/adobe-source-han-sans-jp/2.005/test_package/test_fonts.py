#!/usr/bin/env python3
"""test_package test — Adobe Source Han Sans JP.

Verify that font files were installed into the package fonts/ dir, are
readable, and carry a valid OpenType magic number.
Usage: python3 test_fonts.py <font_dir>
"""
import os
import sys

# OpenType magic numbers (first 4 bytes of the font file):
# - b"\x00\x01\x00\x00" : TrueType-based (glyf outlines)
# - b"OTTO"             : CFF-based (PostScript outlines)
# - b"ttcf"             : TrueType Collection (.ttc / .otc)
VALID_MAGICS = (b"\x00\x01\x00\x00", b"OTTO", b"ttcf")


def main():
    font_dir = sys.argv[1] if len(sys.argv) > 1 else "fonts"
    if not os.path.isdir(font_dir):
        print(f"[fail] font dir not found: {font_dir}")
        sys.exit(1)

    font_exts = (".otf", ".ttf", ".otc", ".ttc")
    fonts = sorted(
        f for f in os.listdir(font_dir) if f.lower().endswith(font_exts)
    )
    print(f"Found {len(fonts)} font files in {font_dir}")

    if not fonts:
        print("[fail] no font files found")
        sys.exit(1)

    # 逐一打开并验证可读性与格式(魔术字节),全部通过后才宣告成功
    for f in fonts:
        fpath = os.path.join(font_dir, f)
        try:
            with open(fpath, "rb") as fh:
                header = fh.read(4)
        except OSError as exc:
            print(f"[fail] cannot read font file: {f} ({exc})")
            sys.exit(1)
        if len(header) < 4:
            print(f"[fail] font file too short: {f}")
            sys.exit(1)
        if header not in VALID_MAGICS:
            print(f"[fail] invalid font magic {header!r}: {f}")
            sys.exit(1)
        print(f"  - {f}")

    print("[ok] font files present and readable")


if __name__ == "__main__":
    main()
