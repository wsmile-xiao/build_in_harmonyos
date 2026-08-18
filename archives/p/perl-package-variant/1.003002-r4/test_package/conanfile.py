#!/usr/bin/env python3
"""Conan test_package — Package::Variant (pure Perl module).

Verifies that Package::Variant can be loaded by Perl.
"""
from conan import ConanFile


class PerlPackageVariantTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Run the test script that verifies Package::Variant can be loaded
        self.run("sh test_variant.sh", env="conanrun")
