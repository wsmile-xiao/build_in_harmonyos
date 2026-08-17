#!/usr/bin/env python3
"""test_xml_parser.py — consumer test source for perl-xml-parser 2.59 (L0c).

Primary path: run XML::Parser with the FULL system perl (usr/local) and
verify the REAL API (R34): version 2.59 + actual XML parse via the expat
XS binding.

Fallback: on CI there is no /storage/Users/currentUser/usr/local/bin/perl
(and the conan perl package lacks Config.pm / dep chain), so degrade to a
pure-Python check of the installed files/version (still exact 2.59).
Usage: test_xml_parser.py <site_perl-dir>
"""
import os
import re
import subprocess
import sys

SYS_PERL = "/storage/Users/currentUser/usr/local/bin/perl"
SYS_SITE = "/storage/Users/currentUser/usr/local/lib/perl5/site_perl/5.42.2"


def find_site(site):
    """Locate the XML/Parser dir under site (handles lib/site_perl and
    lib/perl5/site_perl plus arch subdirs like 5.42.0/aarch64-linux)."""
    for root, _, files in os.walk(site):
        if "Expat.pm" in files and root.endswith(os.path.join("XML", "Parser")):
            return root
    return None


def check_files(site):
    """Pure-Python verification: Expat.pm present + exact version."""
    parser_dir = find_site(site)
    if parser_dir is None:
        raise AssertionError(f"XML/Parser/Expat.pm missing under {site}")
    expat_pm = os.path.join(parser_dir, "Expat.pm")
    with open(expat_pm, "r", errors="replace") as f:
        content = f.read()
    m = re.search(r"\$VERSION\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        raise AssertionError(f"VERSION not found in {expat_pm}")
    version = m.group(1)
    if version != "2.59":
        raise AssertionError(f"version {version} != 2.59")
    print(f"OK: XML::Parser {version} installed ({expat_pm})")


def real_api(site):
    """Full-perl real API test (R34): parse XML via the XS binding."""
    env = {"HOME": os.environ.get("HOME", "")}
    # Expat.pm needs File::ShareDir + Class::Inspector, bundled in THIS
    # test_package dir — include it in PERL5LIB along with our site_perl.
    tp = os.path.dirname(os.path.abspath(__file__))
    env["PERL5LIB"] = os.pathsep.join([site, tp, SYS_SITE])
    # Expat.so links libexpat.so.1 (runtime) — expose its lib dir.
    expat_lib = None
    for root, dirs, files in os.walk("/storage/Users/currentUser/.conan2/p"):
        if "libexpat.so.1" in files:
            expat_lib = root
            break
    if expat_lib:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [expat_lib, env.get("LD_LIBRARY_PATH", "")])
    code = (
        "use strict; use warnings; "
        "use XML::Parser::Expat; "
        "my $v = $XML::Parser::Expat::VERSION; "
        "die qq(version $v != 2.59) unless $v eq '2.59'; "
        "my $p = XML::Parser::Expat->new; "
        "my $tag = ''; "
        "$p->setHandlers(Start => sub { $tag = $_[1]; }); "
        "$p->parse('<hello>world</hello>'); "
        "die qq(parse failed) unless $tag eq 'hello'; "
        "print qq(OK: XML::Parser $v real parse ok\\n)"
    )
    r = subprocess.run([SYS_PERL, "-e", code], capture_output=True,
                       text=True, env=env, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise AssertionError(f"XML::Parser real parse test failed rc={r.returncode}")
    print(r.stdout.strip())


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_xml_parser.py <site_perl-dir>")
    site = sys.argv[1]
    if not os.path.isdir(site):
        raise AssertionError(f"site_perl dir missing: {site}")
    if os.path.isfile(SYS_PERL):
        real_api(site)
    else:
        check_files(site)


if __name__ == "__main__":
    main()
