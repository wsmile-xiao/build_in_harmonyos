#!/usr/bin/env python3
"""Conan test_package — b43-fwcutter 019.

b43-fwcutter is a terminal tool (not a library).
L1 test: verify the binary runs and prints version info.
"""
import os

from conan import ConanFile


class B43FwcutterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Use full path to the installed binary
        dep = self.dependencies["b43-fwcutter"]
        bin_path = os.path.join(dep.package_folder, "bin", "b43-fwcutter")
        self.run(f'"{bin_path}" --version', env="conanrun")
