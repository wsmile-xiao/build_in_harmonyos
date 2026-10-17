#!/usr/bin/env python3
"""Conan test_package for perl-data-dump — R34 real API usage (no empty shell).

Data::Dump is pure Perl. The verifiable artifact is lib/perl5/Data/Dump.pm
under <pkg>/. This test loads the packaged module via perl -I<lib> and
dumps a real nested data structure with dump(), asserting the output
contains the expected fragment — proving the module is loadable and
functional.
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
    if not os.path.isfile(os.path.join(perl5, "Data", "Dump.pm")):
        print(f"FAIL: Data/Dump.pm not found under {perl5}", file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and dump a real data structure.
    perl_prog = (
        "use strict; use Data::Dump qw(dump); "
        "my $d = dump({name => 'hello', nums => [1, 2, 3]}); "
        "my $ok = ($d =~ /hello/ and $d =~ /1, 2, 3/) ? 1 : 0; "
        "print \"Data::Dump loaded, ok=$ok\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Data::Dump loaded" not in r.stdout or "ok=1" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
