#!/usr/bin/env python3
"""astrometry 0.97 consumer test (L0c + R34).

R34: actually exercise the packaged binaries — check solve-field and
wcs-rd2xy exist and print their version/usage banner, and run a real
WCS round-trip through the wcs-rd2xy / wcs-xy2rd tool pair using a
minimal TAN WCS FITS header:

  1. wcs-rd2xy:  RA/Dec (100, 30)  -> pixel, assert it matches CRPIX (512.5).
  2. wcs-xy2rd:  that pixel back  -> RA/Dec, assert it returns (100, 30).

The two calls are inverse operations of each other, so the round-trip
consistency is verified numerically (not just exit-code / non-empty).

Usage: test_astrometry.py <bindir>
"""
import os
import re
import struct
import subprocess
import sys
import tempfile


def _run(cmd, timeout=60):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def _card(keyword, value):
    """Format one 80-char FITS header card."""
    return ("%-8s= %s" % (keyword, value)).ljust(80)[:80]


def _make_fits(path):
    """Write a minimal, legal FITS file with a TAN WCS header.

    NAXIS1=NAXIS2=1 keeps the data block tiny while keeping the file
    fully parseable by cfitsio (header + 2880-byte data block).
    """
    cards = [
        _card("SIMPLE", "T"),
        _card("BITPIX", "-64"),
        _card("NAXIS", "2"),
        _card("NAXIS1", "1"),
        _card("NAXIS2", "1"),
        _card("CTYPE1", "'RA---TAN'"),
        _card("CTYPE2", "'DEC--TAN'"),
        _card("CRVAL1", "100.0"),
        _card("CRVAL2", "30.0"),
        _card("CRPIX1", "512.5"),
        _card("CRPIX2", "512.5"),
        _card("CD1_1", "-0.000277777777777"),
        _card("CD1_2", "0.0"),
        _card("CD2_1", "0.0"),
        _card("CD2_2", "0.000277777777777"),
        _card("END", ""),
    ]
    hdr = "".join(cards)
    hdr = hdr.ljust(2880)  # pad header to a 2880-byte block
    data = struct.pack(">d", 0.0)  # one float64 pixel
    data = data.ljust(2880)  # pad data to a 2880-byte block
    with open(path, "wb") as f:
        f.write(hdr.encode("ascii"))
        f.write(data)


def _parse_last_floats(out, pattern):
    """Find the last line matching `pattern` and return its float groups."""
    matches = re.findall(pattern, out)
    if not matches:
        return None
    groups = matches[-1]
    return [float(g) for g in groups]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    failures = 0

    # 1) Core CLI binaries are installed and print their banner.
    for name in ("solve-field", "wcs-rd2xy", "wcs-xy2rd"):
        exe = os.path.join(bindir, name)
        if not os.path.isfile(exe):
            print(f"FAIL: {name} missing in {bindir}")
            failures += 1
            continue
        rc, out = _run([exe])
        combined = out.lower()
        if "astrometry.net" not in combined and "usage" not in combined:
            print(f"FAIL: {name} banner missing: {out[:200]}")
            failures += 1
        else:
            print(f"OK: {name} present and runnable")

    # 2) Real WCS round-trip on a minimal TAN WCS FITS file.
    #    WCS: CRVAL=(100,30), CRPIX=(512.5,512.5), CD = +-0.000277.../pix
    #    (1 arcsec per pixel).
    workdir = tempfile.mkdtemp(prefix="astrometry-tp-")
    fits = os.path.join(workdir, "t.fits")
    _make_fits(fits)

    rd2xy = os.path.join(bindir, "wcs-rd2xy")
    xy2rd = os.path.join(bindir, "wcs-xy2rd")

    # 2a) sky -> pixel: RA,Dec (100, 30) must map to CRPIX (512.5, 512.5).
    rc, out = _run([rd2xy, "-w", fits, "-r", "100.0", "-d", "30.0"])
    px = _parse_last_floats(
        out, r"RA,Dec\s*\([^)]*\)\s*->\s*pixel\s*\(([-0-9.eE+]+),\s*([-0-9.eE+]+)\)")
    if rc != 0 or px is None:
        print(f"FAIL: wcs-rd2xy: rc={rc} out={out[:300]}")
        failures += 1
    else:
        x, y = px
        if abs(x - 512.5) > 1e-3 or abs(y - 512.5) > 1e-3:
            print(f"FAIL: wcs-rd2xy sky->pixel = ({x:.6f}, {y:.6f}), "
                  f"expected ~(512.5, 512.5)")
            failures += 1
        else:
            print(f"OK: wcs-rd2xy sky->pixel = ({x:.6f}, {y:.6f}) "
                  f"(expect 512.5, 512.5)")

    # 2b) pixel -> sky: feed the pixel from step 2a back in; it must
    #     return RA/Dec (100, 30). This is the inverse of step 2a, so
    #     the pair verifies round-trip consistency.
    if px is not None:
        rc, out = _run([xy2rd, "-w", fits, "-x", "%.6f" % px[0],
                        "-y", "%.6f" % px[1]])
        sky = _parse_last_floats(
            out, r"Pixel\s*\([^)]*\)\s*->\s*RA,Dec\s*\(([-0-9.eE+]+),\s*([-0-9.eE+]+)\)")
        if rc != 0 or sky is None:
            print(f"FAIL: wcs-xy2rd: rc={rc} out={out[:300]}")
            failures += 1
        else:
            ra, dec = sky
            if abs(ra - 100.0) > 1e-4 or abs(dec - 30.0) > 1e-4:
                print(f"FAIL: wcs-xy2rd pixel->sky = ({ra:.6f}, {dec:.6f}), "
                      f"expected ~(100, 30)")
                failures += 1
            else:
                print(f"OK: wcs-xy2rd pixel->sky = ({ra:.6f}, {dec:.6f}) "
                      f"(expect 100, 30) — round-trip OK")

    if failures == 0:
        print("astrometry 0.97 consumer test: OK")
        return 0
    print(f"astrometry 0.97 consumer test: {failures} failures")
    return 1


if __name__ == "__main__":
    sys.exit(main())
