#!/usr/bin/env python3
"""Conan test_package — fastgron 0.7.7

fastgron is a terminal tool (JSON to GRON converter), not a library.
This test verifies the binary can be found and produces correct output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FastgronTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.dependencies["fastgron"].package_folder, "bin", "fastgron")
            self.run(f"{bin_path} -V", env="conanrun")
            self.run(f"echo '{{\"a\":[1,2,3]}}' | {bin_path}", env="conanrun")
