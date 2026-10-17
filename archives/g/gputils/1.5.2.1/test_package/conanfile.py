#!/usr/bin/env python3
"""Conan test_package for gputils 1.5.2.1 — consumer check.

Runs test_gputils.py (standalone test source, satisfies L0c) via self.run
with env="conanrun" (conanrun PATH injection required — see yarl lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GputilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["gputils"].package_folder
        # All three tool directories must be shipped: gplib (and gpvc, gpdasm,
        # gpstrip, gpvo) live in gputils/, and their absence in 1.5.2 is
        # exactly what this revision fixes.
        for rel in ("gpasm/gpasm", "gplink/gplink", "gputils/gplib"):
            if not os.path.isfile(os.path.join(pkg, rel)):
                raise ConanException(f"{rel} missing under {pkg}")
        test_script = os.path.join(os.path.dirname(__file__), "test_gputils.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_gputils.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{pkg}'", env="conanrun")
