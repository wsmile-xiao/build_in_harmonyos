#!/usr/bin/env python3
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class OidentdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "oidentd")
        script = os.path.join(self.recipe_folder, "test_oidentd.py")

        self.run(
            f'"{sys.executable}" "{script}" "{executable}"',
            env="conanrun",
        )
