#!/usr/bin/env python3
"""Conan test_package — astrometry 0.97 consumer test.

R34: the test actually exercises the packaged binaries (solve-field /
wcs-rd2xy / wcs-xy2rd) via an independent test script (test_astrometry.py),
executed through self.run — same pattern as the swarp recipe.
"""
import os

from conan import ConanFile


class AstrometryTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["astrometry"].package_folder
        bindir = os.path.join(pkg, "bin")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_astrometry.py")
        self.run(f"python3 '{test_script}' '{bindir}'", env="conanrun")
