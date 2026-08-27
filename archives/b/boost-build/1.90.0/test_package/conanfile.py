#!/usr/bin/env python3
"""test_package for boost-build — verifies b2 is installed and functional."""
import os

from conan import ConanFile


class BoostBuildTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use explicit path to package binary (R34: test must genuinely depend on package)
        pkg_folder = self.dependencies["boost-build"].package_folder
        b2 = os.path.join(pkg_folder, "bin", "b2")
        self.run(f'B2_PATH="{b2}" sh test.sh', env="conanrun")
