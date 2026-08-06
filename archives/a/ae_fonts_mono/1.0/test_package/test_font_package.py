#!/usr/bin/env python3
"""Consumer test for the ae_fonts_mono data-only package.

Standalone test source (invoked by test_package/conanfile.py via self.run()).
Usage:
    python3 test_font_package.py <package_root>

Verifies that the installed package contains:
  1. share/fonts/ae_fonts_mono/10x21.bdf with the expected size
  2. share/fonts/ae_fonts_mono/10x21.pcf with the expected size
  3. BDF metadata: STARTFONT 2.1 header
  4. BDF metadata: "Public domain font" declaration
  5. PCF magic number \\x01fcp
  6. lib/pkgconfig/ae_fonts_mono.pc whose fontdir resolves to the font dir

Exits 0 when all checks pass, non-zero otherwise.
"""
import os
import sys

EXPECTED_BDF_SIZE = 841126
EXPECTED_PCF_SIZE = 626844
PCF_MAGIC = b"\x01fcp"


def check(cond: bool, message: str) -> None:
    if not cond:
        print(f"[FAIL] {message}", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] {message}")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package_root>", file=sys.stderr)
        return 2
    pkg_root = sys.argv[1]
    if not os.path.isdir(pkg_root):
        print(f"[FAIL] package root not found: {pkg_root}", file=sys.stderr)
        return 1

    font_dir = os.path.join(pkg_root, "share", "fonts", "ae_fonts_mono")
    bdf = os.path.join(font_dir, "10x21.bdf")
    pcf = os.path.join(font_dir, "10x21.pcf")

    # 1. 10x21.bdf exists with the expected size
    check(os.path.isfile(bdf), f"10x21.bdf exists at {bdf}")
    bdf_size = os.path.getsize(bdf)
    check(bdf_size == EXPECTED_BDF_SIZE,
          f"10x21.bdf size == {EXPECTED_BDF_SIZE} (got {bdf_size})")

    # 2. 10x21.pcf exists with the expected size
    check(os.path.isfile(pcf), f"10x21.pcf exists at {pcf}")
    pcf_size = os.path.getsize(pcf)
    check(pcf_size == EXPECTED_PCF_SIZE,
          f"10x21.pcf size == {EXPECTED_PCF_SIZE} (got {pcf_size})")

    # 3. BDF metadata: STARTFONT 2.1 header
    with open(bdf, "rb") as f:
        bdf_head = f.read(1024)
    check(bdf_head.startswith(b"STARTFONT 2.1"), "10x21.bdf starts with STARTFONT 2.1")

    # 4. BDF metadata: public domain declaration
    check(b"Public domain font" in bdf_head,
          "10x21.bdf header declares 'Public domain font'")

    # 5. PCF magic number: 0x01 'f' 'c' 'p'
    with open(pcf, "rb") as f:
        magic = f.read(4)
    check(magic == PCF_MAGIC, f"10x21.pcf magic == {PCF_MAGIC!r} (got {magic!r})")

    # 6. pkg-config file exists and its fontdir resolves to the font dir
    pc = os.path.join(pkg_root, "lib", "pkgconfig", "ae_fonts_mono.pc")
    check(os.path.isfile(pc), f"ae_fonts_mono.pc exists at {pc}")
    with open(pc, "r", encoding="utf-8") as f:
        pc_content = f.read()
    # ${prefix} in the .pc is relative to pcfiledir/../.. (package root)
    resolved_fontdir = os.path.normpath(
        os.path.join(pkg_root, "share", "fonts", "ae_fonts_mono")
    )
    check("fontdir=${prefix}/share/fonts/ae_fonts_mono" in pc_content,
          "ae_fonts_mono.pc declares fontdir=${prefix}/share/fonts/ae_fonts_mono")
    check(resolved_fontdir == os.path.normpath(font_dir),
          f"ae_fonts_mono.pc fontdir resolves to {resolved_fontdir}")

    print(f"[PASS] ae_fonts_mono consumer test: "
          f"10x21.bdf ({bdf_size} B) + 10x21.pcf ({pcf_size} B) verified in {font_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
