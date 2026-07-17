#!/usr/bin/env python3
"""Conan test_package — c2048 1.0.3.

Runs the packaged 2048 command in non-interactive upstream test mode.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class C2048TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["c2048"]
        game = os.path.join(dep.package_folder, "bin", "2048")
        script = os.path.join(self.source_folder, "test_c2048.py")
        self.run(f'python3 "{script}" "{game}"', env="conanrun")
