#!/usr/bin/env python3
"""test_xz.py — CLI consumer test for xz 5.8.1 (R34).

REAL binary check: compress a temp file with the packaged xz CLI and
decompress it back (round-trip proves the CLI + embedded liblzma work).
Usage: test_xz.py <xz-bin-dir>
"""
import os
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_xz.py <xz-bin-dir>")
    bindir = sys.argv[1]
    xz = os.path.join(bindir, "xz")
    if not os.path.isfile(xz):
        raise AssertionError(f"xz binary missing: {xz}")
    data = b"hello xz harmonyos " * 100
    with tempfile.TemporaryDirectory() as tmp:
        plain = os.path.join(tmp, "t.bin")
        comp = os.path.join(tmp, "t.bin.xz")
        with open(plain, "wb") as f:
            f.write(data)
        r = subprocess.run([xz, "-k", plain], capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise SystemExit(f"xz compress failed (rc={r.returncode})")
        if not os.path.isfile(comp):
            raise AssertionError("xz compressed output missing")
        r2 = subprocess.run([xz, "-d", "-k", comp, "-c"], capture_output=True)
        if r2.returncode != 0:
            raise SystemExit(f"xz decompress failed (rc={r2.returncode})")
        if r2.stdout != data:
            raise AssertionError("xz round-trip data mismatch")
    print("OK: xz 5.8.1 CLI round-trip ok (compress/decompress)")


if __name__ == "__main__":
    main()
