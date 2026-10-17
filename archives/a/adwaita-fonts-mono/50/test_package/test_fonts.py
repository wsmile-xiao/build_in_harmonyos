#!/usr/bin/env python3
"""Font validation for adwaita-fonts-mono 50.

Checks that the installed font directory contains exactly the expected
4 Adwaita Mono TTF files, all non-empty, with valid TrueType magic bytes.
Also verifies that Adwaita Sans files are NOT present (mono-only boundary).
"""
import os
import sys

# Expected Mono TTF files
EXPECTED_FONTS = [
    "AdwaitaMono-Bold.ttf",
    "AdwaitaMono-BoldItalic.ttf",
    "AdwaitaMono-Italic.ttf",
    "AdwaitaMono-Regular.ttf",
]

# TTF files that must NOT be installed (mono-only boundary)
EXCLUDED_FONTS = [
    "AdwaitaSans-Italic.ttf",
    "AdwaitaSans-Regular.ttf",
]

# Valid TrueType/OpenType magic bytes
VALID_MAGIC = {b"\x00\x01\x00\x00", b"true"}


def validate_fonts(font_dir: str) -> int:
    """Validate font files in the given directory. Returns 0 on success, 1 on failure."""
    errors = []

    if not os.path.isdir(font_dir):
        print(f"FAIL: Font directory not found: {font_dir}")
        return 1

    # Check expected Mono fonts exist, are non-empty, and have valid magic
    for font_name in EXPECTED_FONTS:
        font_path = os.path.join(font_dir, font_name)
        if not os.path.isfile(font_path):
            errors.append(f"Missing font file: {font_name}")
            continue

        size = os.path.getsize(font_path)
        if size == 0:
            errors.append(f"Empty font file: {font_name} (0 bytes)")
            continue

        with open(font_path, "rb") as f:
            magic = f.read(4)
        if magic not in VALID_MAGIC:
            errors.append(
                f"Invalid TTF magic in {font_name}: "
                f"got {magic.hex()!r}, expected 00010000 or 74727565"
            )
        print(f"  OK  {font_name} ({size} bytes, magic={magic.hex()})")

    # Check that excluded Sans fonts are NOT present
    for font_name in EXCLUDED_FONTS:
        font_path = os.path.join(font_dir, font_name)
        if os.path.isfile(font_path):
            errors.append(
                f"Sans font found in mono-only package: {font_name}"
            )
        else:
            print(f"  OK  {font_name} — correctly excluded")

    if errors:
        print("\nFAIL: " + "\n".join(errors))
        return 1

    print(f"\nAll {len(EXPECTED_FONTS)} TTF fonts validated successfully")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_fonts.py <font_directory>")
        sys.exit(1)
    sys.exit(validate_fonts(sys.argv[1]))