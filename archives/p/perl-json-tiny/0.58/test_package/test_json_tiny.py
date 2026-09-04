#!/usr/bin/env python3
"""Conan test_package for perl-json-tiny — R34 real API usage (no empty shell).

JSON::Tiny is pure Perl. The verifiable artifact is lib/perl5/JSON/Tiny.pm
under <pkg>/. This test loads the packaged module via perl -I<lib> and
encodes/decodes a real JSON structure with encode_json()/decode_json(),
asserting the round-trip — proving the module is loadable and functional.
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
    if not os.path.isfile(os.path.join(perl5, "JSON", "Tiny.pm")):
        print(f"FAIL: JSON/Tiny.pm not found under {perl5}", file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and round-trip a real JSON structure.
    perl_prog = (
        "use strict; use JSON::Tiny qw(encode_json decode_json); "
        "my $h = {name => 'hello', nums => [1, 2, 3]}; "
        "my $j = encode_json($h); "
        "my $d = decode_json($j); "
        "my $ok = ($d->{name} eq 'hello' and $d->{nums}[1] == 2) ? 1 : 0; "
        "print \"JSON::Tiny loaded, ok=$ok\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "JSON::Tiny loaded" not in r.stdout or "ok=1" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
