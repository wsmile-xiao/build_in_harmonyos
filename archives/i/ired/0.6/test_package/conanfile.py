#!/usr/bin/env python3
"""Consumer test recipe for ired 0.6.

Runs the installed `ired` binary against a real hex-editing workflow:
writes bytes, reads them back, and searches a pattern — verifying that a
third-party consumer can execute the installed CLI on HarmonyOS.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class IredTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            self.output.info("ired consumer test skipped: target cannot run")
            return

        package = self.dependencies["ired"].package_folder
        bin_dir = os.path.join(package, "bin")
        script = os.path.join(self.recipe_folder, "test_ired.py")
        self.run(
            f'"{sys.executable}" "{script}" "{bin_dir}"',
            env="conanrun",
        )
