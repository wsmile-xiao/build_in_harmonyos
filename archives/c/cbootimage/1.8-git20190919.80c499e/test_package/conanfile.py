#!/usr/bin/env python3
"""Conan test_package — executes the packaged cbootimage binary (R34).

cbootimage is a standalone CLI tool (no libraries), so the consumer test
runs the installed binary and asserts its usage output instead of linking.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CbootimageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies["cbootimage"].cpp_info.bindirs[0]
        exe = os.path.join(self.build_folder, bin_dir, "cbootimage")
        if can_run(self):
            # cbootimage/1.8 has no --version/--help; running without args
            # prints a usage line ("Usage: cbootimage ...") to stderr and
            # exits non-zero.  Assert the usage line is produced (R34: real
            # execution of the packaged binary, no echo/print stub).
            self.run(f"{exe} 2>&1 | grep 'Usage: cbootimage'", env="conanrun")