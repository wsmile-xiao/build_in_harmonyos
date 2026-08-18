#!/usr/bin/env python3
"""test_uri.py — L0c-visible test source for perl-uri 5.35.

L0c requires a .c/.cpp/.py test source file in test_package/ (a bare
.pl is not recognized by the static scan — CI L0c no_test_sources).
This .py source drives the packaged URI via perl (test_uri.pl) so the
real-API verification still runs.
Usage: test_uri.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_uri.py <site-perl-dir>")
    site = sys.argv[1]
    if not os.path.isfile(os.path.join(site, "URI.pm")):
        raise AssertionError(f"URI.pm missing under {site}")
    script = os.path.join(os.path.dirname(__file__), "test_uri.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_uri.pl missing: {script}")
    # absolute perl path — conanrun PATH may not carry perl into subprocess
    r = subprocess.run(["/data/service/hnp/bin/perl",
                        script, site], capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl uri check failed (rc={r.returncode})")
    print("OK: perl-uri 5.35 python-driven check")


if __name__ == "__main__":
    main()
