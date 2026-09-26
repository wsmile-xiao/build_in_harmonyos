#!/usr/bin/env python3
"""Conan test_package for mrename 1.2."""
import os
import shutil

from conan import ConanFile


class MrenameTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_mrename.sh")
        mrename = os.path.join(pkg_folder, "bin", "mrename")
        shell = shutil.which("sh") or "/bin/sh"
        self.run(f'"{shell}" "{script}" "{mrename}" "{pkg_folder}"',
                 env="conanrun")
