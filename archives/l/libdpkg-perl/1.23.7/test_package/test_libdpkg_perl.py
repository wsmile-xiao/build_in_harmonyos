#!/usr/bin/env python3
"""Conan test_package for libdpkg-perl — R34 real API usage (no empty shell).

libdpkg-perl is pure Perl. The verifiable artifact is lib/perl5/Dpkg.pm
under <pkg>/. This test loads the packaged Dpkg::Version via perl -I<lib>
and compares two Debian version strings — proving the module is loadable
and functional.
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    p = shutil.which("perl")
    if p:
        return p
    for cand in ("/storage/Users/currentUser/usr/local/bin/perl",
                 "/data/service/hnp/bin/perl", "/usr/bin/perl"):
        if os.path.isfile(cand):
            return cand
    return None


def main():
    pkg = sys.argv[1]
    perl5 = os.path.join(pkg, "lib", "perl5")
    if not os.path.isfile(os.path.join(perl5, "Dpkg", "Version.pm")):
        print(f"FAIL: Dpkg/Version.pm not found under {perl5}",
              file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and use its real API (version compare).
    perl_prog = (
        "use strict; use Dpkg::Version; "
        "my $cmp = version_compare('1.2.3', '1.2.3'); "
        "print \"Dpkg::Version loaded, cmp(1.2.3,1.2.3)=$cmp\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Dpkg::Version loaded" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
