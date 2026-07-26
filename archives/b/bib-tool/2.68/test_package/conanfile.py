#!/usr/bin/env python3
"""Conan test_package for bib-tool — verifies the bibtool binary works.

R34: Test must actually depend on the tested package.
bibtool is a CLI tool — the test runs the binary via test_bibtool.sh.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BibtoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary via test_bibtool.sh
        dep = self.dependencies["bib-tool"]
        bibtool_bin = os.path.join(dep.package_folder, "usr", "local", "bin", "bibtool")
        test_script = os.path.join(self.source_folder, "test_bibtool.sh")
        if can_run(self):
            self.run(
                f'sh "{test_script}" "{bibtool_bin}"',
                env="conanrun",
            )
