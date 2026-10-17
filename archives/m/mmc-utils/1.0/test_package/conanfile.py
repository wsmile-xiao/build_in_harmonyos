#!/usr/bin/env python3
import os
import sys

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class MmcUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "mmc")
        smoke = os.path.join(self.recipe_folder, "test_mmc_utils.py")
        consumer = os.path.join(self.recipe_folder, "test_consumer_mmc.py")

        # smoke test: mmc help usage table and version string
        self.run(
            f'"{sys.executable}" "{smoke}" "{executable}"',
            env="conanrun",
        )

        # HarmonyOS-specific test: complete end-to-end consumer case (rule 12),
        # synthetic SD card directory feeding the installed mmc, result checked
        self.run(
            f'"{sys.executable}" "{consumer}" "{executable}"',
            env="conanrun",
        )
