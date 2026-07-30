#!/usr/bin/env python3
"""Conan test_package — pidof 2.86 CLI tool verification.

pidof is a CLI tool, not a library, so the test uses VirtualRunEnv to locate
the installed binary and drives it against a real background process (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PidofTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bin_dir = self.dependencies["pidof"].cpp_info.bindirs[0]
        pidof_bin = os.path.join(bin_dir, "pidof")
        test_script = os.path.join(self.source_folder, "test_pidof.sh")
        self.run(f'sh "{test_script}" "{pidof_bin}"', env="conanrun")
