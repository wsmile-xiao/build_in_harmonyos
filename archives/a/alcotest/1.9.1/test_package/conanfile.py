#!/usr/bin/env python3
"""Conan test_package for alcotest — OCaml library validation.

Since alcotest is an OCaml library (not a C/C++ library), we cannot
use CMake to test it. Instead, we verify that the package files exist
and are valid using a shell script.
"""
import os

from conan import ConanFile


class AlcotestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["alcotest"].package_folder
        self.run(f"bash {os.path.join(self.source_folder, 'test_alcotest.sh')} {pkg_folder}",
                 env="conanrun")
