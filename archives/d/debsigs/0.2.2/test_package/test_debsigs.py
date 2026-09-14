#!/usr/bin/env python3
"""debsigs consumer test (R34): execute the real installed binary.

Check 1: `debsigs --version` exits 0 and prints `debsigs v0.2.2`.
Check 2: `debsigs --features` exits 0 and its `debsigs` entry agrees with
  --version (mirrors upstream test_features.py::test_version).
Both checks execute the packaged script with the packaged Perl modules
(PERL5LIB=<pkg>/lib/perl5); a missing/corrupt/non-runnable binary fails.
"""
import os
import re
import subprocess
import sys


def _perl():
    for cand in ("/data/service/hnp/bin/perl", "/usr/bin/perl"):
        if os.path.isfile(cand):
            return cand
    return "perl"


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    binary = os.path.join(pkg, "bin", "debsigs")
    if not os.path.isfile(binary):
        print("FAIL: debsigs binary not found: %s" % binary, file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PERL5LIB"] = os.path.join(pkg, "lib", "perl5")
    perl = _perl()

    r = subprocess.run([perl, binary, "--version"],
                       capture_output=True, text=True, env=env, timeout=60)
    if r.returncode != 0:
        print("FAIL: debsigs --version rc=%s: %s" % (r.returncode, (r.stderr or r.stdout).strip()[:500]),
              file=sys.stderr)
        return 1
    version_out = (r.stdout or r.stderr).strip().splitlines()
    if not version_out or version_out[0].strip() != "debsigs v0.2.2":
        print("FAIL: unexpected --version output: %r" % (version_out[:3],), file=sys.stderr)
        return 1
    print("OK [1/2]: %s" % version_out[0].strip())

    r2 = subprocess.run([perl, binary, "--features"],
                        capture_output=True, text=True, env=env, timeout=60)
    if r2.returncode != 0:
        print("FAIL: debsigs --features rc=%s: %s" % (r2.returncode, (r2.stderr or r2.stdout).strip()[:500]),
              file=sys.stderr)
        return 1
    feat_out = r2.stdout or ""
    m = re.search(r"debsigs[=\s]+([^\s,;]+)", feat_out)
    if not m or m.group(1).strip() != "0.2.2":
        print("FAIL: --features debsigs entry missing version 0.2.2: %r" % (feat_out[:300],),
              file=sys.stderr)
        return 1
    print("OK [2/2]: --features agrees (%s)" % m.group(0).strip())
    print("HMBS_TEST_PACKAGE_RESULT=" + '{"executed":true,"passed":true,'
          '"command":"debsigs --version + --features","discovered":2,"passedCount":2}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
