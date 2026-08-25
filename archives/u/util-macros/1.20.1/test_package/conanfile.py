#!/usr/bin/env python3
"""Conan test_package for util-macros 1.20.1.

R34: Verifies xorg-macros.m4 is installed in the correct
aclocal directory and contains expected macro definitions.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UtilMacrosTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        pkg_root = pkg.package_folder

        test_script = os.path.join(self.source_folder, "test.sh")
        bash = "/data/service/hnp/bin/bash"
        self.run(f'{bash} "{test_script}" "{pkg_root}"')
