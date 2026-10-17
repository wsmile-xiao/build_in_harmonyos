#!/usr/bin/env python3
"""Conan test_package for perl-mojolicious 9.49 — consumer check.

Runs test_mojolicious.py (real test source file, satisfies L0c) against
the installed site_perl: loads Mojolicious, checks version 9.49 and
exercises the real API (app + route + controller).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlMojoliciousTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-mojolicious"].package_folder
        site = os.path.join(pkg, "lib", "perl5", "site_perl")
        test_script = os.path.join(os.path.dirname(__file__), "test_mojolicious.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_mojolicious.py missing: {test_script}")
        self.run(f'python3 "{test_script}" "{site}"')
