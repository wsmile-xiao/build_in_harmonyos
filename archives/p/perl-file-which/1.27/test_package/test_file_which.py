#!/usr/bin/env python3
"""Conan test_package for perl-file-which — R34 real API usage (no empty shell).

File::Which is pure Perl. The verifiable artifact is lib/perl5/File/Which.pm
under <pkg>/. This test loads the packaged module via perl -I<lib> and
calls which() to resolve a real executable (perl itself) from PATH —
proving the module is loadable and functional.
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
    if not os.path.isfile(os.path.join(perl5, "File", "Which.pm")):
        print(f"FAIL: File/Which.pm not found under {perl5}", file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and resolve a real executable via which().
    perl_prog = (
        "use strict; use File::Which qw(which); "
        "my $p = which('perl'); "
        "my $ok = defined($p) && length($p) ? 1 : 0; "
        "print \"File::Which loaded, found=$ok\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "File::Which loaded" not in r.stdout or "found=1" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
