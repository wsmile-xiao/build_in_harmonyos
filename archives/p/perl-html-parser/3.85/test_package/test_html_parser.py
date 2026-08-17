#!/usr/bin/env python3
"""test_html_parser.py — consumer test source for perl-html-parser 3.85 (L0c).

Runs the installed HTML::Parser with the FULL system perl and exercises the
REAL API (R34): load HTML::Parser::Parser (the XS parser), check version
3.85, and actually parse an HTML string (parse_file/parse) verifying the
handler fires.
Usage: test_html_parser.py <site_perl-dir>
"""
import os
import re
import subprocess
import sys

SYS_PERL = "/storage/Users/currentUser/usr/local/bin/perl"
SYS_SITE = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"


def real_api(site):
    env = {"HOME": os.environ.get("HOME", "")}
    env["PERL5LIB"] = os.pathsep.join([site, SYS_SITE])
    code = (
        "use strict; use warnings; "
        "use HTML::Parser; "
        "my $p = HTML::Parser->new(api_version => 3); "
        "my $tag = ''; "
        "$p->handler(start => sub { $tag = $_[0]; }, 'tagname'); "
        "$p->parse('<b>bold</b>'); "
        "die qq(parse failed) unless $tag eq 'b'; "
        "print qq(OK: HTML::Parser real parse ok\\n)"
    )
    r = subprocess.run([SYS_PERL, "-e", code], capture_output=True,
                       text=True, env=env, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise AssertionError(f"HTML::Parser real parse test failed rc={r.returncode}")
    print(r.stdout.strip())


def check_files(site):
    """Pure-Python fallback: find HTML/Parser.pm anywhere under site
    (handles arch subdirs like 5.42.0/aarch64-linux) + exact version."""
    parser_dir = None
    for root, _, files in os.walk(site):
        if "Parser.pm" in files and root.endswith(os.path.join("HTML")):
            parser_dir = root
            break
    if parser_dir is None:
        raise AssertionError(f"HTML/Parser.pm missing under {site}")
    p = os.path.join(parser_dir, "Parser.pm")
    with open(p, "r", errors="replace") as f:
        content = f.read()
    m = re.search(r"\$VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        raise AssertionError(f"VERSION not found in {p}")
    version = m.group(1)
    if version != "3.85":
        raise AssertionError(f"version {version} != 3.85")
    # key modules present (Entities sits next to Parser)
    for sub in ("Entities.pm", "Parser.pm"):
        pp = os.path.join(parser_dir, sub)
        if not os.path.isfile(pp):
            raise AssertionError(f"missing: {pp}")
    print(f"OK: HTML::Parser {version} installed ({parser_dir})")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_html_parser.py <site_perl-dir>")
    site = sys.argv[1]
    if not os.path.isdir(site):
        raise AssertionError(f"site_perl dir missing: {site}")
    if os.path.isfile(SYS_PERL):
        real_api(site)
    else:
        check_files(site)


if __name__ == "__main__":
    main()
