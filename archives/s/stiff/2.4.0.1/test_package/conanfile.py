#!/usr/bin/env python3
"""Conan consumer test for STIFF."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class StiffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        binary = os.path.join(self.dependencies["stiff"].package_folder, "bin", "stiff")
        script = os.path.join(self.source_folder, "test_stiff.py")
        self.run(f'python3 "{script}" "{binary}"', env="conanrun")
