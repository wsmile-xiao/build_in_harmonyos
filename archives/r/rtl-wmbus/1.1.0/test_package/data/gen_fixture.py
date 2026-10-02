#!/usr/bin/env python3
"""Regenerate data/issue48.cu8.gz.b64 (the IQ fixture used by the test binaries).

Provenance
----------
Upstream ``samples/rtlsdr_868.625M_2M4_issue48.cu8`` from the official rtl-wmbus
1.1.0 tag archive (sha256
0da72c7f5b026a4c0d8dc9beabba021f147c950f52eb8e09f4e41884d4f32ebf).

Why a prefix
------------
The full capture is 204800 bytes but the decoder only locks on once the
preamble/clock-recovery front end has consumed ~180 KB of lead-in. Empirically
(``for n in $(seq 4096 4096 204800); do head -c $n ... | rtl_wmbus -d 3 -s -o``)
176 KiB yields nothing while 180224 bytes yields the full telegram pair, and the
truncated input decodes to output byte-identical to the complete file
(verified for both the native x86 and the OHOS aarch64 build).

Why base64(gzip(...))
---------------------
R02: the shared CI checkout receives packages as a patch and ``git apply``
cannot reconstruct binary patch data ("cannot apply binary patch ... without
full index line"), so raw ``.cu8`` must not be committed. Same approach as
``archives/l/libmysofa/1.3.5/test_package/data/testfile.sofa.b64``.
gzip is applied first so the committed text is 160 KB instead of 243 KB; it is
undone at build time by CMakeLists.txt using only the python3 standard library.

Usage::

    python3 gen_fixture.py <path-to-extracted-samples-dir>
"""
import base64
import gzip
import os
import sys

PREFIX_BYTES = 180224
SAMPLE = "rtlsdr_868.625M_2M4_issue48.cu8"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "issue48.cu8.gz.b64")


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    src = os.path.join(sys.argv[1], SAMPLE)
    with open(src, "rb") as fh:
        raw = fh.read(PREFIX_BYTES)
    if len(raw) != PREFIX_BYTES:
        sys.stderr.write(f"{src}: expected at least {PREFIX_BYTES} bytes\n")
        return 1
    # mtime=0 keeps the output byte-reproducible.
    packed = base64.b64encode(gzip.compress(raw, 9, mtime=0)).decode("ascii")
    lines = [packed[i:i + 76] for i in range(0, len(packed), 76)]
    with open(OUT, "w", encoding="ascii") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"{SAMPLE}: {PREFIX_BYTES} raw bytes -> {len(raw)} -> "
          f"{len(gzip.compress(raw, 9, mtime=0))} gzip -> "
          f"{os.path.getsize(OUT)} base64 bytes -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
