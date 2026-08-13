#!/usr/bin/env python3
"""Conan test_package for perl-strictures — verifies Perl module can be loaded and enforces strict mode."""
import os

from conan import ConanFile


class PerlstricturesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["perl-strictures"]
        perl_lib = os.path.join(dep.package_folder, "lib")
        test_script = os.path.join(self.source_folder, "run_test.sh")
        self.run(f'sh "{test_script}" "{perl_lib}"')
