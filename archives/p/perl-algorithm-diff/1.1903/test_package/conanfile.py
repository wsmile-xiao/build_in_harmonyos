#!/usr/bin/env python3
"""Conan test_package for perl-algorithm-diff — runs the R34 consumer check.

L1 official test: runs a Python script that loads the packaged
Algorithm::Diff via perl -I<lib> and computes a real diff between two
arrays. R34 real API usage, not just file presence.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["perl-algorithm-diff"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_algorithm_diff.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
