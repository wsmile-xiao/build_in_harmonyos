#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/h/hivex/1.3.24/test_package/conanfile.py
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import chdir

import os


class HivexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # The consumer binary is driven directly as well, so the CI log carries
        # the complete per-assertion transcript (L0d/R34) rather than only
        # ctest's one-line summary.  It is run from the binary directory, where
        # CMakeLists.txt has copied the `minimal.b64` hive fixture (base64 text;
        # the test decodes it to a real hive image at runtime).
        with chdir(self, self.build_folder):
            exe = os.path.join(self.build_folder, "test_hivex")
            self.run(f'"{exe}" minimal.b64 hivex-test-out.hive')
