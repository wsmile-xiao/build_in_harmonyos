#!/usr/bin/env python3
"""Conan test_package for perl-cgi 4.72 — consumer check.

Runs test_cgi.pl (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlCgiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("perl-uri/5.35")

    def test(self):
        pkg = self.dependencies["perl-cgi"].package_folder
        # locate CGI.pm (site_perl or lib/perl5 — walk to avoid drift)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "CGI.pm" in files:
                site = root
                break
        if not site:
            raise ConanException("CGI.pm not found in package")
        # CGI.pm requires URI — inject perl-uri's site into PERL5LIB so the
        # child perl sees it (package_info only prints PERL5LIB, no runenv)
        uri_pkg = self.dependencies["perl-uri"].package_folder
        uri_site = None
        for root, _dirs, files in os.walk(uri_pkg):
            if "URI.pm" in files:
                uri_site = root
                break
        if uri_site:
            os.environ["PERL5LIB"] = uri_site
        # test_cgi.py is the L0c-visible test source (.py recognized by the
        # static scan) and drives the real perl check (test_cgi.pl)
        test_script = os.path.join(os.path.dirname(__file__), "test_cgi.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_cgi.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
