#!/usr/bin/env python3
"""Conan test_package for perl-test-harness — R34 real API usage (no empty shell).

Test::Harness is pure Perl. The verifiable artifact is lib/perl5/TAP/... and
bin/prove under <pkg>/. This test loads the packaged TAP::Harness via perl
-I<lib> and creates a real TAP::Harness instance — proving the modules are
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
    if not os.path.isfile(os.path.join(perl5, "TAP", "Harness.pm")):
        print(f"FAIL: TAP/Harness.pm not found under {perl5}",
              file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and construct a real object.
    perl_prog = (
        "use strict; use TAP::Harness; "
        "my $harness = TAP::Harness->new({verbosity => 0}); "
        "print 'TAP::Harness loaded, jobs=' . ($harness->{jobs} // '?') "
        ". \"\\n\";"
    )
    r = subprocess.run([perl, f"-I{perl5}", "-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "TAP::Harness loaded" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")

    # Also verify bin/prove exists + runnable via perl (shebang /usr/bin/perl
    # does not exist in OHOS sandbox — invoke through resolved perl).
    # NOTE: `prove --version` prints "TAP::Harness vX.Y and Perl vZ..." — assert
    # on that banner (prove itself is not echoed literally), rc==0 proves runnable.
    prove = os.path.join(pkg, "bin", "prove")
    if not os.path.isfile(prove):
        print(f"FAIL: bin/prove not found in {pkg}", file=sys.stderr)
        return 1
    r2 = subprocess.run([perl, prove, "--version"], capture_output=True,
                        text=True)
    out2 = (r2.stdout or "").strip()
    if r2.returncode != 0 or "TAP::Harness" not in out2:
        print(f"FAIL: prove --version rc={r2.returncode}, unexpected: "
              f"{out2[:200]}", file=sys.stderr)
        return 1
    print(f"OK: bin/prove present + runnable: {out2.splitlines()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
