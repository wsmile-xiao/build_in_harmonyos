#!/usr/bin/env python3
"""Conan test_package for farbfeld 4."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class FarbfeldTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        package_folder = self.dependencies["farbfeld"].package_folder
        ff2ppm = os.path.join(package_folder, "bin", "ff2ppm")
        if not os.path.isfile(ff2ppm):
            raise AssertionError(f"ff2ppm binary not found: {ff2ppm}")

        test_script = os.path.join(self.source_folder, "test_farbfeld.py")
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(test_script),
                shlex.quote(os.path.join(package_folder, "bin")),
            ),
            env="conanrun",
        )
