#!/usr/bin/env python3
"""test_package for spek-cli — L1 test.

Delegates to test.sh which verifies package product structure (bin/spek-cli
entry, executable bit, --help usage) and runs the CLI smoke test. HMDFS
noexec on dev hosts blocks exec'ing the ELF binary; CI workers can exec.
self.run() is the literal call CI L0d gate (grep -q "self\.run") scans for.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class SpekTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        pkg = self.dependencies["spek"]
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'bash "{test_sh}" "{pkg.package_folder}"',
            env="conanrun",
        )
