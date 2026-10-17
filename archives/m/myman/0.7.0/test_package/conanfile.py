#!/usr/bin/env python3
"""Consumer checks for myman 0.7.0."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class MymanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skip running myman")
            return
        package = self.dependencies["myman"].package_folder
        executable = os.path.join(package, "bin", "myman")
        script = os.path.join(os.path.dirname(__file__), "test_myman.py")
        self.run(f'"{sys.executable}" "{script}" "{executable}"', env="conanrun")
