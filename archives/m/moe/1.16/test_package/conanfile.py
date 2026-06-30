#!/usr/bin/env python3
"""Conan test_package — moe 1.16.

moe is a terminal text editor (executable), not a library.
This test verifies the binary can run and report its version.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class MoeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the moe binary in the dependency package
        moe_pkg = self.dependencies["moe"]
        bin_path = None
        for bindir in moe_pkg.cpp_info.bindirs:
            candidate = os.path.join(bindir, "moe")
            if os.path.exists(candidate):
                bin_path = candidate
                break
        if not bin_path:
            # Fallback: search in package_folder
            pkg_folder = moe_pkg.package_folder
            candidate = os.path.join(pkg_folder, "bin", "moe")
            if os.path.exists(candidate):
                bin_path = candidate
        if bin_path:
            self.run(f'"{bin_path}" --version', env="conanrun")
        else:
            raise Exception("moe binary not found in package")
