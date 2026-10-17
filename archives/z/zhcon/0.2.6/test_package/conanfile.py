#!/usr/bin/env python3
"""Conan test_package — zhcon 0.2.6 L1 smoke test.

zhcon is a CLI application (no library to link). This test runs the
test.sh functional smoke test: verifies the installed binary is present
and actually runs (`zhcon --version` / `zhcon --help` exit 0), zhcon.conf
config profile exists, and input-method data files are shipped.
"""
import os

from conan import ConanFile


class ZhconTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # expose the installed package root so test.sh can locate the binary,
        # zhcon.conf and the input-method data directory deterministically.
        zhcon_pkg = self.dependencies["zhcon"].package_folder
        self.run(f"CONAN_PACKAGE_ROOT={zhcon_pkg} {bash} test.sh", env="conanrun")