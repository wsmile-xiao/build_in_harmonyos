#!/usr/bin/env python3
"""Conan test_package for spin — verifies binary integrity via static analysis."""
import os

from conan import ConanFile


class SpinTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify spin binary is in PATH
        self.run("which spin", env="conanrun")
        # Verify binary is a valid ELF for arm64
        self.run("file $(which spin) | grep -q 'ELF.*arm64'", env="conanrun")
        # Verify ELF architecture via readelf
        self.run("readelf -h $(which spin) | grep -q 'AArch64'", env="conanrun")
        # Verify expected version string embedded in binary
        self.run("strings $(which spin) | grep -q 'Spin Version'", env="conanrun")
        # Verify spin has main entry point symbol
        self.run("nm $(which spin) 2>/dev/null | grep -q 'main'", env="conanrun")
