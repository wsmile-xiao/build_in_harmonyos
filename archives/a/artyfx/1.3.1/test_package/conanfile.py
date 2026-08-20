#!/usr/bin/env python3
"""Conan test_package for artyfx 1.3.1.

This test loads the built artyfx.so via dlopen and verifies:
1. The shared library can be loaded
2. It exports the lv2_descriptor symbol
3. The returned LV2_Descriptor has a valid URI
4. Multiple LV2 plugins are discoverable

This satisfies R34: test_package must actually exercise the built package.
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArtyfxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Find the installed artyfx.so in the package folder
        pkg_folder = self.dependencies["artyfx"].package_folder
        so_candidates = glob.glob(os.path.join(pkg_folder, "**", "artyfx.so"), recursive=True)
        if not so_candidates:
            so_path = os.path.join(pkg_folder, "lib", "lv2", "artyfx.lv2", "artyfx.so")
        else:
            so_path = so_candidates[0]

        self.output.info(f"Testing artyfx.so at: {so_path}")

        # Run the test binary directly with ARTYFX_SO_PATH env var
        test_bin = os.path.join(self.build_folder, "test_artyfx")
        self.run(f'ARTYFX_SO_PATH="{so_path}" "{test_bin}"', env=["conanrun"])
