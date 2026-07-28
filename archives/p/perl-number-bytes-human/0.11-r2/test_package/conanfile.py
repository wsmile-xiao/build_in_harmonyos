#!/usr/bin/env python3
"""Conan test_package — perl-number-bytes-human (Number::Bytes::Human) 0.11-r2

L1 test: verify the Perl module can be loaded and reports correct version.
"""
from conan import ConanFile


class PerlnumberbyteshumanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed for a pure Perl module test
        pass

    def test(self):
        # Verify the module loads and reports the correct version
        self.run("./test_module.sh", env="conanrun")
