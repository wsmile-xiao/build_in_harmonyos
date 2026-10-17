#!/usr/bin/env python3
"""Conan test_package for perl-test-exception — R34 real API usage (no empty shell).

Test::Exception is pure Perl. The verifiable artifact is lib/perl5/Test/
Exception.pm under <pkg>/. This test loads the packaged module via
perl -I<lib> (injecting dependency perl-sub-uplevel's lib/perl5), calls
throws_ok() to verify a real exception — proving the module is loadable
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
    dep_pkg = sys.argv[2] if len(sys.argv) > 2 else None
    perl5 = os.path.join(pkg, "lib", "perl5")
    if not os.path.isfile(os.path.join(perl5, "Test", "Exception.pm")):
        print(f"FAIL: Test/Exception.pm not found under {perl5}", file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and run a real exception test.
    # 需要注入依赖 perl-sub-uplevel 的 lib/perl5（Sub::Uplevel）
    inc = [f"-I{perl5}"]
    if dep_pkg:
        dep_perl5 = os.path.join(dep_pkg, "lib", "perl5")
        if os.path.isdir(dep_perl5):
            inc.append(f"-I{dep_perl5}")
    perl_prog = (
        "use strict; use Test::More tests => 1; use Test::Exception (); "
        "my $threw = 0; "
        "eval { Test::Exception::dies_ok(sub { die 'boom-test' }, 'dies ok'); "
        "       $threw = 1 if $@ =~ /boom-test/; }; "
        "print \"Test::Exception loaded, ran=$threw\\n\";"
    )
    r = subprocess.run([perl] + inc + ["-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Test::Exception loaded" not in r.stdout or "ran=1" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
