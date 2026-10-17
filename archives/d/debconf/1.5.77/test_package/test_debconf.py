#!/usr/bin/env python3
"""Conan test_package for debconf — R34 real API usage (no empty shell).

debconf is pure Perl. The verifiable artifact is the Debconf::* module tree
under <pkg>/lib/perl5/ plus the debconf-* CLI scripts in <pkg>/bin/.
This test actually loads the packaged Debconf::Priority module through perl
(-I<lib>) and calls its real exported API (priority_valid/priority_list),
then runs the packaged `debconf-escape` helper — proving the modules load
and the scripts are runnable.
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """Locate the perl interpreter (not on PATH inside conanrun env)."""
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
    if not os.path.isdir(perl5):
        print(f"FAIL: perl5 lib dir not found: {perl5}")
        return 1

    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged Debconf::Priority module and call its real API.
    # Debconf::Priority is self-contained (only depends on Debconf::Config,
    # whose package-level $config defaults are fine for these pure functions),
    # and exports priority_valid/priority_list with no I/O side effects.
    perl_prog = (
        "use strict; use Debconf::Priority qw(priority_valid priority_list); "
        "my @prios = priority_list(); "
        "my $ok = (priority_valid('high') ? 'yes' : 'no'); "
        "print 'Debconf::Priority loaded, priorities=' . join(',', @prios) "
        ". \" high_valid=$ok\\n\";"
    )
    r = subprocess.run(
        [perl, f"-I{perl5}", "-e", perl_prog],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl Debconf::Priority load rc={r.returncode}: "
              f"{r.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    out = r.stdout.strip()
    if "Debconf::Priority loaded" not in out:
        print(f"FAIL: unexpected output: {out[:200]}", file=sys.stderr)
        return 1
    if "high_valid=yes" not in out:
        print(f"FAIL: priority_valid('high') should be yes: {out[:200]}",
              file=sys.stderr)
        return 1
    print(f"OK: {out}")

    # Also verify a packaged CLI script is present + runnable.
    # NOTE: the script shebang is `#!/usr/bin/perl`, which does not exist in
    # the OHOS sandbox (perl lives under /storage/Users/currentUser/usr/local/
    # bin), so invoke it through the resolved perl interpreter. debconf-escape
    # escapes/unescapes BACKSLASH + newline (not URL percent-encoding):
    #   -e: "\" -> "\\", "\n" -> literal "\n"
    #   -u: "\n" -> real newline. Input "a\nb" (backslash-n) -> "a<NL>b".
    escape = os.path.join(pkg, "bin", "debconf-escape")
    if not os.path.isfile(escape):
        print(f"FAIL: bin/debconf-escape not found in {pkg}", file=sys.stderr)
        return 1
    # feed literal backslash-n via stdin: 'a\\nb' -> expect 'a\nb' (real NL)
    r2 = subprocess.run([perl, escape, "-u"], input="a\\nb",
                        capture_output=True, text=True)
    unescaped = (r2.stdout or "")
    if unescaped != "a\nb":
        print(f"FAIL: debconf-escape -u expected 'a<NL>b', got "
              f"{unescaped!r} (rc={r2.returncode})", file=sys.stderr)
        return 1
    print("OK: debconf-escape present + runnable, -u unescapes '\\n' correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
