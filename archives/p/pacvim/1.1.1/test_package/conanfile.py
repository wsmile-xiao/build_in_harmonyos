#!/usr/bin/env python3
"""Conan test_package — pacvim 1.1.1.

Verifies the packaged pacvim binary runs and produces expected output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PacvimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["pacvim"]
        game = os.path.join(dep.package_folder, "bin", "pacvim")
        script = os.path.join(self.source_folder, "test_pacvim.py")
        self.run(f'python3 "{script}" "{game}" "{dep.package_folder}"', env="conanrun")
