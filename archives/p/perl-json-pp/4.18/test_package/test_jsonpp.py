#!/usr/bin/env python3
"""test_jsonpp.py — L0c-visible test source for perl-json-pp 4.18.

L0c requires a .c/.cpp/.py test source file in test_package/ (a bare
.pl is not recognized by the static scan — CI L0c no_test_sources).
This .py source drives the packaged JSON::PP via perl (test_jsonpp.pl)
so the real-API verification still runs through the module.
Usage: test_jsonpp.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_jsonpp.py <site-perl-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "JSON")):
        raise AssertionError(f"JSON dir missing under {site}")
    script = os.path.join(os.path.dirname(__file__), "test_jsonpp.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_jsonpp.pl missing: {script}")
    # absolute perl path — conanrun PATH may not carry perl into subprocess
    r = subprocess.run(["/data/service/hnp/bin/perl",
                        script, site], capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl json-pp check failed (rc={r.returncode})")
    print("OK: perl-json-pp 4.18 python-driven check")


if __name__ == "__main__":
    main()
