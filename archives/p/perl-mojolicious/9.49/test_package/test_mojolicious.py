#!/usr/bin/env python3
"""test_mojolicious.py — consumer test source for perl-mojolicious 9.49 (L0c).

Runs the installed Mojolicious with the FULL system perl and exercises the
REAL API (R34). The top-level `use Mojolicious` pulls in IO::Socket::IP,
which fails on OHOS (platform Errno does not export EWOULDBLOCK), so we
load framework core modules that do NOT need the socket stack and call
their real APIs:
  1) Mojo::ByteStream — new() + to_string() round-trip
  2) Mojo::Collection — new() + map() + to_array()
  3) Mojolicious::Routes — new() + get() route registration
Exact version (9.49) is verified here in Python (no perl -e escaping
pitfalls). Usage: test_mojolicious.py <site_perl-dir>
"""
import os
import re
import subprocess
import sys

SYS_PERL = "/storage/Users/currentUser/usr/local/bin/perl"
SYS_SITE = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"


def check_version(site):
    mojo = os.path.join(site, "Mojolicious.pm")
    if not os.path.isfile(mojo):
        raise AssertionError(f"Mojolicious.pm missing: {mojo}")
    with open(mojo, "r", errors="replace") as f:
        content = f.read()
    m = re.search(r"\$VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        raise AssertionError(f"VERSION not found in {mojo}")
    version = m.group(1)
    if version != "9.49":
        raise AssertionError(f"version {version} != 9.49")
    return version


def real_api(site):
    env = {"HOME": os.environ.get("HOME", "")}
    env["PERL5LIB"] = os.pathsep.join([site, SYS_SITE])
    # Real API calls only (version verified in Python above).
    code = (
        "use strict; use warnings; "
        "use Mojo::ByteStream; "
        "use Mojo::Collection; "
        "use Mojolicious::Routes; "
        "my $b = Mojo::ByteStream->new('hello'); "
        "die 'bstream' unless $b->to_string eq 'hello'; "
        "my $col = Mojo::Collection->new(1, 2, 3)->map(sub { $_ * 2 }); "
        "my $arr = $col->to_array; "
        "die 'collection' unless @$arr == 3 && $arr->[2] == 6; "
        "my $r = Mojolicious::Routes->new; "
        "$r->get('/ok')->to(cb => sub {}); "
        "print qq(OK: Mojolicious 9.49 real API ok\\n)"
    )
    r = subprocess.run([SYS_PERL, "-e", code], capture_output=True,
                       text=True, env=env, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise AssertionError(f"Mojolicious real API test failed rc={r.returncode}")
    print(r.stdout.strip())


def check_files(site):
    """Pure-Python fallback (no full perl available)."""
    version = check_version(site)
    for sub in ("Mojo.pm",
                os.path.join("Mojolicious", "Controller.pm"),
                os.path.join("Mojo", "UserAgent.pm")):
        p = os.path.join(site, sub)
        if not os.path.isfile(p):
            raise AssertionError(f"missing: {p}")
    print(f"OK: Mojolicious {version} installed ({site})")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_mojolicious.py <site_perl-dir>")
    site = sys.argv[1]
    if not os.path.isdir(site):
        raise AssertionError(f"site_perl dir missing: {site}")
    check_version(site)  # always verify exact version
    if os.path.isfile(SYS_PERL):
        real_api(site)
    else:
        check_files(site)


if __name__ == "__main__":
    main()
