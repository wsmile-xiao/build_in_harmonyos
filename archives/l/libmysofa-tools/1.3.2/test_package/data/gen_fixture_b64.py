#!/usr/bin/env python3
"""Regenerate test_package/data/testfile.sofa.b64 from the OFFICIAL upstream
tarball (validated generation path, R02 fixture strategy).

The R01 PR carried a raw binary fixture (test_package/data/testfile.sofa),
which the shared CI checkout (git apply of the platform PR diff) cannot
deliver: binary files appear as "Binary files differ" without patch data,
so `git apply`/`git apply --3way` fail with "cannot apply binary patch ...
without full index line" (reproduced on CI main 720939d0a).

This task replaces the binary fixture with its base64 text encoding, kept in
git as a normal text file, and regenerates the real .sofa at test_package
build time. The generation path is fully validated and reproducible:

  1. official tarball   https://github.com/hoene/libmysofa/archive/refs/tags/v1.3.2.tar.gz
     sha256 6c5224562895977e87698a64cb7031361803d136057bba35ed4979b69ab4ba76
  2. extract            libmysofa-1.3.2/tests/tester.sofa
     sha256 38abbb518e4e43ec2efbd4765e763e764776f18ae0e0181f3684bff644d9c58b
  3. base64 (whole-file, 76-col wrapped) -> testfile.sofa.b64 (this file)

Any change to the upstream fixture changes its sha256 and the .b64 content,
and CI conandata sha256 check would fail - the .b64 cannot silently drift
from the official source.
"""
import base64
import hashlib
import sys

FIXTURE_SHA256 = "38abbb518e4e43ec2efbd4765e763e764776f18ae0e0181f3684bff644d9c58b"


def main():
    if len(sys.argv) != 3:
        print("usage: gen_fixture_b64.py <tester.sofa> <output.b64>", file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    with open(src, "rb") as fh:
        data = fh.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != FIXTURE_SHA256:
        print(f"sha256 mismatch: got {digest}, expected {FIXTURE_SHA256}", file=sys.stderr)
        return 1
    enc = base64.b64encode(data).decode("ascii")
    lines = [enc[i:i + 76] for i in range(0, len(enc), 76)]
    with open(out, "w", encoding="ascii") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
