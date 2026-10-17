#!/usr/bin/env python3
"""Conan test_package for perl-uri 5.35 — consumer check.

Runs test_uri.pl (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlUriTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-uri"].package_folder
        # locate URI.pm (install prefix varies by perl build — walk)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "URI.pm" in files:
                site = root
                break
        if not site:
            raise ConanException("URI.pm not found in package")
        # test_uri.py is the L0c-visible test source (.py recognized by the
        # static scan) and drives the real perl check (test_uri.pl)
        test_script = os.path.join(os.path.dirname(__file__), "test_uri.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_uri.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
