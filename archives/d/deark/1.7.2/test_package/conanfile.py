#!/usr/bin/env python3
"""Conan test_package for deark 1.7.2.

R34: Test must actually depend on the tested package.
deark is a CLI tool — the test runs test_deark.sh which verifies
the binary's version, module listing, and license output.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DearkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary via test_deark.sh
        dep = self.dependencies["deark"]
        deark_bin = os.path.join(dep.package_folder, "bin", "deark")
        test_script = os.path.join(self.source_folder, "test_deark.sh")

        if can_run(self):
            self.run(
                f'sh "{test_script}" "{deark_bin}"',
                env="conanrun",
            )
