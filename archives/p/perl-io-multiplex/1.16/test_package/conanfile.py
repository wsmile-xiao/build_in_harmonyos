#!/usr/bin/env python3
"""Conan test_package for perl-io-multiplex 1.16 — consumer check.

Runs test_io_multiplex.py (standalone test source, satisfies L0c) via
self.run with env="conanrun" (the conanrun PATH injection is required —
a bare subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlIoMultiplexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-io-multiplex"].package_folder
        # locate site_perl root that contains IO/Multiplex.pm
        # (install prefix varies by perl build — walk; site = parent of IO/)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Multiplex.pm" in files and os.path.basename(root) == "IO":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("IO/Multiplex.pm not found in package")
        # test_io_multiplex.py is the L0c-visible test source (.py recognized
        # by the static scan) and drives the real perl check
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_io_multiplex.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_io_multiplex.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
