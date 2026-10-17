#!/usr/bin/env python3
"""test_libwww.py — consumer test source for perl-libwww 6.83 (L0c).

Primary path: run LWP with the FULL system perl (usr/local — has the dep
chain HTTP::Request/URI/... not published to ohpcd) and verify the REAL
API (R34): version exactly 6.83 + create UserAgent + agent round-trip.

Fallback: on CI there is no /storage/Users/currentUser/usr/local/bin/perl
(and the conan perl package lacks Config.pm / dep chain), so degrade to a
pure-Python check of the installed files/version (still exact 6.83).
Usage: test_libwww.py <site_perl-dir>
"""
import os
import re
import subprocess
import sys

SYS_PERL = "/storage/Users/currentUser/usr/local/bin/perl"
SYS_SITE = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"


def check_files(site):
    """Pure-Python verification: files present + exact version."""
    ua = os.path.join(site, "LWP", "UserAgent.pm")
    if not os.path.isfile(ua):
        raise AssertionError(f"LWP/UserAgent.pm missing: {ua}")
    with open(ua, "r", errors="replace") as f:
        content = f.read()
    m = re.search(r"\$VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        raise AssertionError(f"VERSION not found in {ua}")
    version = m.group(1)
    if version != "6.83":
        raise AssertionError(f"version {version} != 6.83")
    for sub in ("LWP.pm", os.path.join("LWP", "Protocol.pm"),
                os.path.join("LWP", "ConnCache.pm")):
        p = os.path.join(site, sub)
        if not os.path.isfile(p):
            raise AssertionError(f"missing: {p}")
    print(f"OK: LWP::UserAgent {version} installed ({site})")


def real_api(site):
    """Full-perl real API test (R34)."""
    env = {"HOME": os.environ.get("HOME", "")}
    env["PERL5LIB"] = os.pathsep.join([site, SYS_SITE])
    code = (
        "use strict; use warnings; "
        "use LWP::UserAgent; "
        "my $v = $LWP::UserAgent::VERSION; "
        "die qq(version $v != 6.83) unless $v eq '6.83'; "
        "my $ua = LWP::UserAgent->new(agent => 'test/1.0', timeout => 5); "
        "die qq(agent mismatch) unless $ua->agent eq 'test/1.0'; "
        "print qq(OK: LWP::UserAgent $v real API ok\\n)"
    )
    r = subprocess.run([SYS_PERL, "-e", code], capture_output=True,
                       text=True, env=env, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise AssertionError(f"LWP real API test failed rc={r.returncode}")
    print(r.stdout.strip())


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_libwww.py <site_perl-dir>")
    site = sys.argv[1]
    if not os.path.isdir(site):
        raise AssertionError(f"site_perl dir missing: {site}")
    if os.path.isfile(SYS_PERL):
        real_api(site)
    else:
        # CI has no full perl — degrade to pure-Python check (still exact)
        check_files(site)


if __name__ == "__main__":
    main()
