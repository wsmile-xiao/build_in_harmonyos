#!/usr/bin/env python3
"""Conan test_package for perl-html-parser 3.85 — consumer check.

Runs test_html_parser.py (real test source file, satisfies L0c) against
the installed site_perl: loads HTML::Parser and actually parses HTML
(real API, R34).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlHtmlParserTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-html-parser"].package_folder
        # Locate the site_perl dir dynamically (CI's conan perl uses
        # lib/site_perl/<ver>/<arch>/; local system perl lib/perl5/site_perl)
        site = None
        for root, _, files in os.walk(pkg):
            if "Parser.pm" in files and root.endswith(os.path.join("HTML")):
                site = os.path.dirname(os.path.dirname(root))
                break
        if not site:
            raise ConanException(f"HTML/Parser.pm not found in {pkg}")
        test_script = os.path.join(os.path.dirname(__file__), "test_html_parser.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_html_parser.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')
