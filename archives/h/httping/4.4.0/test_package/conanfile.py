#!/usr/bin/env python3
"""Conan test_package for httping 4.4.0."""

import os

from conan import ConanFile


class HttpingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        httping = os.path.join(self.dependencies["httping"].package_folder, "bin", "httping")
        self.run(f'"{httping}" -V', env="conanrun")
        self.run(f'"{httping}" --help', env="conanrun")
