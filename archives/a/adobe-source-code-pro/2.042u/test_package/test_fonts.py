#!/usr/bin/env python3
"""Verify Source Code Pro upright font files: existence, count, non-empty,
TTF magic header, and sha256 baselines."""

import hashlib
import os
import struct
import sys


def main():
    pkg_folder = sys.argv[1] if len(sys.argv) > 1 else ""
    font_dir = os.path.join(pkg_folder, "share", "fonts", "SourceCodePro")

    if not os.path.isdir(font_dir):
        print(f"[FAIL] font dir not found: {font_dir}")
        sys.exit(1)

    expected = {
        "SourceCodePro-Black.ttf": "37a4fd8a65b8d27580676cf956e8af3a2a6204dbc76dec4318ad0fed660bc89d",
        "SourceCodePro-Bold.ttf": "b2095e0d657e6d28dc32444a9dacabab0c9241d0bf39d96371756cc9bdbc3a5f",
        "SourceCodePro-ExtraLight.ttf": "8f4deb0901f375797fe51c2351abf2059e4ebbab2ec0ac390d040c3e802ddec6",
        "SourceCodePro-Light.ttf": "e9bb1870b0765b2cf06f797039d3dba4a78bb90360b20840bfc6a0c024d8f756",
        "SourceCodePro-Medium.ttf": "f9dbc746f60c83f5cb1503b19f90729d8195cab6bb67f2b861d4eb257ed86536",
        "SourceCodePro-Regular.ttf": "74bd80d3e42a08517cd7e1108ba3d86f2da29ac0f3065be95e0357956ab9db37",
        "SourceCodePro-Semibold.ttf": "014a0fdf42504ee1faf719a96eab5f9ffdade793f1d5c5729ad4606f2aedc765",
    }

    files = sorted(os.listdir(font_dir))
    ttf_files = [f for f in files if f.endswith(".ttf")]
    print(f"[INFO] Found files: {files}")
    if len(ttf_files) != 7:
        print(f"[FAIL] Expected 7 upright TTF files, found {len(ttf_files)}")
        sys.exit(1)
    print(f"[PASS] file count OK (7 upright TTF)")

    errors = []
    for fname, exp_sha in expected.items():
        path = os.path.join(font_dir, fname)
        if not os.path.isfile(path):
            errors.append(f"Missing font file: {fname}")
            continue
        size = os.path.getsize(path)
        with open(path, "rb") as fp:
            header = fp.read(4)
        if len(header) < 4:
            errors.append(f"Font file too small: {fname} ({size} bytes)")
            continue
        magic = struct.unpack(">I", header)[0]
        if magic != 0x00010000:
            errors.append(f"Invalid TTF magic in {fname}: {magic:#010x}")
        with open(path, "rb") as fp:
            actual = hashlib.sha256(fp.read()).hexdigest()
        if actual != exp_sha:
            errors.append(f"sha256 mismatch for {fname}: expected {exp_sha}, got {actual}")
        else:
            print(f"[PASS] {fname}: {size} bytes, magic 0x00010000, sha256 OK")

    if errors:
        print("\n".join(f"[FAIL] {e}" for e in errors))
        sys.exit(1)

    print(f"[PASS] All 7 upright font files verified in {font_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
