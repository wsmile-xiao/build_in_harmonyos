#!/usr/bin/env python3
"""Conan test_package for nextvi 7."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class NextviTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping run")
            return
        if self.settings.os == "Windows":
            self.output.info("nextvi uses POSIX terminal APIs; skipping Windows smoke")
            return
        vi_path = os.path.join(self.dependencies["nextvi"].package_folder, "bin", "vi")
        test_script = os.path.join(self.source_folder, "test_nextvi.py")
        self.run(f'"{sys.executable}" "{test_script}" "{vi_path}"', env="conanrun")
