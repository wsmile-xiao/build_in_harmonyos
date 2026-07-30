#!/usr/bin/env python3
"""Conan test_package for ttaenc 3.4.1.

Verifies that the ttaenc binary is functional after installation.
Runs ttaenc -v (version) and ttaenc -h (help) to confirm the binary works.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TtaencTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["ttaenc"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            ttaenc_cmd = os.path.join(bin_dir, "ttaenc")

            # Run functional test script (version, help, encode WAV→TTA)
            test_script = os.path.join(self.source_folder, "test_ttaenc.sh")
            self.run(f'sh "{test_script}" "{ttaenc_cmd}"', env="conanrun")
