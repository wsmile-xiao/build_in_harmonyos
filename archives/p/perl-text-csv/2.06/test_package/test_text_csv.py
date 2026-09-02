#!/usr/bin/env python3
"""Conan test_package for perl-text-csv — R34 real API usage (no empty shell).

Text::CSV with the bundled pure-Perl PP backend. The verifiable artifact is
lib/perl5/Text/CSV.pm + CSV_PP.pm under <pkg>/. This test loads the packaged
module via perl -I<lib> (PERL_TEXT_CSV=0 forces PP backend) and parses a real
CSV string, asserting fields — proving the module is loadable and functional.
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
    if not os.path.isfile(os.path.join(perl5, "Text", "CSV.pm")) \
       or not os.path.isfile(os.path.join(perl5, "Text", "CSV_PP.pm")):
        print(f"FAIL: Text/CSV.pm or CSV_PP.pm not found under {perl5}",
              file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and parse a real CSV string.
    # PERL_TEXT_CSV=0 forces the bundled pure-Perl PP backend (no XS .so).
    env = dict(os.environ)
    env["PERL_TEXT_CSV"] = "0"
    perl_prog = (
        "use strict; use Text::CSV; "
        "my $csv = Text::CSV->new({binary=>1}) or die Text::CSV->error_diag; "
        "my $ok = $csv->parse(\"a,b,c\\n\"); "
        "my @f = $csv->fields(); "
        "print \"Text::CSV loaded, ok=$ok, fields=\" . scalar(@f) . \"\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Text::CSV loaded" not in r.stdout or "fields=3" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
