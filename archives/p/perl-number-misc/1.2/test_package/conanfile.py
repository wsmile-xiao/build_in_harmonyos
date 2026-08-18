#!/usr/bin/env python3
"""Conan test_package — perl-number-misc (Number::Misc) 1.2

L1 test: verify the Perl module can be loaded and its core API works.
"""
from conan import ConanFile


class PerlnumbermiscTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed for a pure Perl module test
        pass

    def test(self):
        # Verify the module loads and its core API (is_numeric) works correctly
        # exit(0) on success, exit(1) on failure — Conan catches non-zero exit
        self.run('perl -MNumber::Misc -e "exit(Number::Misc::is_numeric(q{123}) ? 0 : 1)"', env="conanrun")
