#!/usr/bin/env python3
"""Conan test_package for grepcidr 2.0 — verifies grepcidr binary works.

grepcidr is a CLI tool (not a library), so we test by running the binary
with functional test cases (version check, CIDR matching, non-matching).
"""
import os

from conan import ConanFile


class GrepcidrTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        grepcidr_bin = os.path.join(self.dependencies["grepcidr"].package_folder, "bin", "grepcidr")
        test_script = os.path.join(self.source_folder, "test_grepcidr.sh")
        self.run(f'sh "{test_script}" "{grepcidr_bin}"')
