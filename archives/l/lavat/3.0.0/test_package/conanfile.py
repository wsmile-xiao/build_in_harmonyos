#!/usr/bin/env python3
"""Conan test_package for lavat 3.0.0 — binary smoke test.

Verifies that the lavat binary is functional after installation.
Runs lavat -h to check it starts and prints help output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LavatTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["lavat"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{bin_dir}:$PATH" '
                f'bash test.sh',
                env="conanrun"
            )
