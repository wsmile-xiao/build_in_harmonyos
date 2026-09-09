#!/usr/bin/env python3
"""Conan test recipe for afl++-tools — tool-type package shell test."""
import os

from conan import ConanFile


class TestAflToolsConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile a simple test program using the installed AFL++ headers.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        include_dir = os.path.join(
            self.dependencies["afl++-tools"].package_folder, "include", "afl"
        )
        test_src = os.path.join(self.source_folder, "test_afl.c")
        test_bin = os.path.join(self.build_folder, "test_afl")

        self.run(
            '{} -I"{}" -o "{}" "{}"'.format(cc, include_dir, test_bin, test_src)
        )

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_afl")
        self.run(test_bin, env="conanrun")
