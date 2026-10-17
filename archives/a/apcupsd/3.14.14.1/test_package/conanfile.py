#!/usr/bin/env python3
"""Conan test_package for apcupsd — verifies the built binary works.

Test: Run `apcupsd --version` to verify the installed binary is functional.
This is an L1 consumer test (R34: test must call the tested package's binary).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ApcupsdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["apcupsd"]
            binary = os.path.join(pkg.package_folder, "sbin", "apcupsd")
            self.run(f'"{binary}" --version', env="conanrun")
