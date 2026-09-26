#!/usr/bin/env python3
"""Conan test_package — qprint 1.1.dfsg.2 (Conan L1 official test).

Consumer test: encode/decode roundtrip + known-value assertion via the
installed qprint binary (R34: real use of the packaged executable).
"""
import os

from conan import ConanFile


class QprintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = None
        for _, dep in self.dependencies.items():
            pkg_folder = dep.package_folder
            break
        bin_path = os.path.join(pkg_folder, "bin", "qprint")
        self.run(f'sh test.sh "{bin_path}"', env="conanrun")
