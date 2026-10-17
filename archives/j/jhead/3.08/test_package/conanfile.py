#!/usr/bin/env python3
"""Conan test_package for jhead 3.08.

R34: Test must actually depend on the tested package.
jhead is a CLI tool — the test runs the binary directly.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class JheadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["jhead"]
        jhead_bin = os.path.join(dep.package_folder, "bin", "jhead")
        if can_run(self):
            # Test 1: Version check (jhead -V prints version and exits 0)
            self.run(f'"{jhead_bin}" -V', env="conanrun")
            # Test 2: Run test_jhead.sh for version + help output verification
            test_dir = os.path.dirname(__file__)
            self.run(f'zsh "{test_dir}/test_jhead.sh" "{jhead_bin}"', env="conanrun")
