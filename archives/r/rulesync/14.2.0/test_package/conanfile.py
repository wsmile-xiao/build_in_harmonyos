#!/usr/bin/env python3
"""Test package — rulesync 14.2.0 consumer test."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class RulesyncTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["rulesync"].package_folder
            executable = os.path.join(
                package_folder,
                "bin",
                "rulesync",
            ).replace("\\", "/")
            test_script = os.path.join(
                self.source_folder,
                "test.sh",
            ).replace("\\", "/")
            self.run(
                f'sh "{test_script}" "{executable}"',
                cwd=self.source_folder,
                env="conanrun",
            )
