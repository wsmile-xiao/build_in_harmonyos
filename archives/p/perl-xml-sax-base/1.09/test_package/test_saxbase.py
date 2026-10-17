#!/usr/bin/env python3
"""test_saxbase.py — L0c-visible test source for perl-xml-sax-base 1.09.

L0c requires a .c/.cpp/.py test source file in test_package/ (a bare
.pl is not recognized by the static scan — CI L0c no_test_sources).
This .py source drives the packaged XML::SAX::Base via perl
(test_saxbase.pl) so the real-API verification still runs.
Usage: test_saxbase.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_saxbase.py <site-perl-dir>")
    site = sys.argv[1]
    if not os.path.isfile(os.path.join(site, "XML", "SAX", "Base.pm")):
        raise AssertionError(f"XML/SAX/Base.pm missing under {site}")
    script = os.path.join(os.path.dirname(__file__), "test_saxbase.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_saxbase.pl missing: {script}")
    # absolute perl path — CI-accessible (hnp), not local usr/local
    r = subprocess.run(["/data/service/hnp/bin/perl", script, site],
                       capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl sax-base check failed (rc={r.returncode})")
    print("OK: perl-xml-sax-base 1.09 python-driven check")


if __name__ == "__main__":
    main()
