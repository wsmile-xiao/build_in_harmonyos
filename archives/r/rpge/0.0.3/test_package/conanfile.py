#!/usr/bin/env python3
"""Consumer checks for the installed RPGE executable."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class RpgeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        package = self.dependencies[self.tested_reference_str]
        executable = os.path.join(package.package_folder, "usr", "bin", "rpge")
        script = os.path.join(self.recipe_folder, "test_commands.py")
        self.run(f'"{sys.executable}" "{script}" "{executable}"', env="conanrun")
