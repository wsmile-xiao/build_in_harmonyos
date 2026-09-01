#!/usr/bin/env python3
"""Conan test_package for perl-text-diff — runs the R34 consumer check.

L1 official test: runs a Python script that loads the packaged
Text::Diff via perl -I<lib> and computes a real diff between two
text strings. R34 real API usage, not just file presence.
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
            pkg = self.dependencies["perl-text-diff"].package_folder
            # perl-text-diff 依赖 perl-algorithm-diff——test 需同时注入其 lib/perl5
            dep_pkg = self.dependencies["perl-algorithm-diff"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_text_diff.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}" "{dep_pkg}"',
                     env="conanrun")
