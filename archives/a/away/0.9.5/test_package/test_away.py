#!/usr/bin/env python3
"""away consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

away is a PAM terminal locking program; running it needs a PAM
session / terminal locking (/etc/pam.d/away system install + OHOS
terminal/PAM session model differences — environment limitation,
honest). This script verifies the packaged binary is present,
executable and a valid ELF (R34 degraded check).

Usage: test_away.py <package-folder>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "away")
    pam_conf = os.path.join(pkg, "etc", "pam.d", "away.pam")
    if not os.path.isfile(exe):
        raise AssertionError(f"away binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"away not executable: {exe}")
    if not os.path.isfile(pam_conf):
        raise AssertionError(f"away.pam config missing: {pam_conf}")
    with open(exe, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"away is not an ELF binary: {exe}")
    print(f"OK: away binary present and executable ({exe})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
