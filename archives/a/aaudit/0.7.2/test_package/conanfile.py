#!/usr/bin/env python3
"""Conan test_package — aaudit 0.7.2 L1 smoke test."""
import os
from conan import ConanFile


class AauditTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify aaudit binary is present and runs --help successfully
        aaudit = os.path.join(self.dependencies["aaudit"].package_folder,
                              "bin", "aaudit")
        if not os.path.isfile(aaudit):
            raise RuntimeError(f"aaudit not found at {aaudit}")
        self.run(f"/bin/sh test_aaudit.sh {aaudit}", env="conanrun")