#!/usr/bin/env python3
"""Conan test_package for perl-test-simple — R34 real API usage (no empty shell).

Test::Simple is pure Perl. The verifiable artifact is lib/perl5/Test/Simple.pm
(+ Test/More.pm) under <pkg>/. This test loads the packaged module via
perl -I<lib> and runs a real ok() assertion — proving the module is
loadable and functional.
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
    if not os.path.isfile(os.path.join(perl5, "Test", "Simple.pm")) \
       or not os.path.isfile(os.path.join(perl5, "Test", "More.pm")):
        print(f"FAIL: Test/Simple.pm or Test/More.pm not found under {perl5}",
              file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and run a real ok() assertion.
    perl_prog = (
        "use strict; use Test::Simple tests => 1; "
        "ok(1 + 1 == 2, 'one plus one is two'); "
        "print \"Test::Simple loaded\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Test::Simple loaded" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
