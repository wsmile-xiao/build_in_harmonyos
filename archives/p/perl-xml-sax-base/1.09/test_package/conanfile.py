#!/usr/bin/env python3
"""Conan test_package for perl-xml-sax-base 1.09 — consumer check.

Runs test_saxbase.py (L0c-visible .py test source) via self.run with
env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlXmlSaxBaseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-xml-sax-base"].package_folder
        # locate XML/SAX/Base.pm — site-perl root = dirname(dirname(SAX/))
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Base.pm" in files and os.path.basename(root) == "SAX":
                site = os.path.dirname(os.path.dirname(root))
                break
        if not site:
            raise ConanException("XML/SAX/Base.pm not found in package")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_saxbase.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_saxbase.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
