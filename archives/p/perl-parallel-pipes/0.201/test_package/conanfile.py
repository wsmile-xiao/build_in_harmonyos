#!/usr/bin/env python3
"""Conan test_package — Parallel::Pipes (pure Perl module)."""
import os

from conan import ConanFile


class PerlparallelpipesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-parallel-pipes"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(self.source_folder, "test_pipes.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"')
