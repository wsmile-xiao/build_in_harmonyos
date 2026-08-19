#!/usr/bin/env python3
"""test_cgi.py — L0c-visible test source for perl-cgi 4.72.

L0c requires a .c/.cpp/.py test source file in test_package/ (a bare
.pl is not recognized by the static scan — CI L0c no_test_sources).
This .py source drives the packaged CGI via perl (test_cgi.pl) so the
real-API verification still runs.
Usage: test_cgi.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_cgi.py <site-perl-dir>")
    site = sys.argv[1]
    if not os.path.isfile(os.path.join(site, "CGI.pm")):
        raise AssertionError(f"CGI.pm missing under {site}")
    script = os.path.join(os.path.dirname(__file__), "test_cgi.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_cgi.pl missing: {script}")
    # absolute perl path — conanrun PATH may not carry perl into subprocess
    r = subprocess.run(["/data/service/hnp/bin/perl",
                        script, site], capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl cgi check failed (rc={r.returncode})")
    print("OK: perl-cgi 4.72 python-driven check")


if __name__ == "__main__":
    main()
