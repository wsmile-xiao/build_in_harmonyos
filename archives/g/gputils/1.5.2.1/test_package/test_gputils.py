#!/usr/bin/env python3
"""test_gputils.py — consumer test source for gputils 1.5.2.1 (L0c).

REAL API check (R34):
  1. every shipped tool exists and answers --version (gpasm/gplink live in
     their own directories, the other five in gputils/);
  2. the packaged gpasm really assembles a minimal PIC16 program and the
     .hex output ends with the Intel-HEX EOF record.

Usage: test_gputils.py <package-folder>

Regression guard: 1.5.2 shipped without gplib/gpvc/gpdasm because the
packaging list named non-existent per-tool directories. sdcc's PIC14/PIC16
ports need gpasm AND gplink AND gplib, so the missing tools must fail here.
"""
import os
import subprocess
import sys
import tempfile

# tool name -> path relative to the package folder
TOOLS = {
    "gpasm": "gpasm/gpasm",
    "gplink": "gplink/gplink",
    "gpdasm": "gputils/gpdasm",
    "gplib": "gputils/gplib",
    "gpstrip": "gputils/gpstrip",
    "gpvo": "gputils/gpvo",
    "gpvc": "gputils/gpvc",
}


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_gputils.py <package-folder>")
    pkg = sys.argv[1]

    # (1) presence + executability + version banner for every tool
    for name, rel in sorted(TOOLS.items()):
        path = os.path.join(pkg, rel)
        if not os.path.isfile(path):
            raise AssertionError(f"{name} missing: {path}")
        r = subprocess.run([path, "--version"], capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(
                f"{name} --version failed (rc={r.returncode}): "
                f"{(r.stderr or r.stdout or '').strip()[:200]}")

    # (2) gpasm really assembles; PIC processor headers live in header/
    header_dir = os.path.join(pkg, "header")
    asm = ("    list p=16f877\n"
           "    include \"p16f877.inc\"\n"
           "    org 0\n"
           "start\n"
           "    goto start\n"
           "    end\n")
    with tempfile.TemporaryDirectory() as tmp:
        asm_file = os.path.join(tmp, "t.asm")
        with open(asm_file, "w") as f:
            f.write(asm)
        r = subprocess.run([os.path.join(pkg, "gpasm", "gpasm"),
                            "-I", header_dir, asm_file],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise AssertionError(f"gpasm failed with rc={r.returncode}")
        hex_file = os.path.join(tmp, "t.hex")
        if not os.path.isfile(hex_file):
            raise AssertionError(f".hex output missing: {hex_file}")
        with open(hex_file, "r") as f:
            content = f.read()
        if ":00000001FF" not in content:
            raise AssertionError(f".hex missing end-of-file record: {content!r}")
    print("OK: gputils 1.5.2.1 consumer check "
          "(7 tools present + gpasm assembled t.hex)")


if __name__ == "__main__":
    main()
