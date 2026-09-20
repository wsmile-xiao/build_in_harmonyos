#!/usr/bin/env python3
"""Conan test_package for boinc-client 8.0.4 — smoke test for CLI binaries.

Runs test.sh which:
1. Verifies boinc_client and boinccmd binaries exist in PATH
2. Checks ELF format and binary size
3. Executes --help / --version to verify binaries are functional
"""
import os

from conan import ConanFile


class BoincclientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{test_script}"', env="conanrun")
