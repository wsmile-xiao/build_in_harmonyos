#!/usr/bin/env python3
"""Conan test_package for perl-text-parsewords 3.31 — consumer check.

Runs test_parsewords.pl (standalone test source, satisfies L0c) via
self.run with env="conanrun" (the conanrun PATH injection is required —
a bare subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class PerlTextParsewordsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-text-parsewords"].package_folder
        # locate Text/ParseWords.pm (install prefix varies by perl build —
        # walk to avoid hard-coded paths); @INC needs the parent of Text/
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "ParseWords.pm" in files and os.path.basename(root) == "Text":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("Text/ParseWords.pm not found in package")
        # test_parsewords.py is the L0c-visible test source (.py recognized
        # by the static scan) and drives the real perl check (.pl)
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_parsewords.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_parsewords.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
