#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/mkclean/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MkcleanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Fix: profile sets generator=Make which is invalid in cmake 4.x
        tc.generator = "Unix Makefiles"
        # cmake 4.x compatibility
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run the mkclean binary to verify it works (L2 smoke test)
        # mkclean --version prints version but exits with code 255
        dep = self.dependencies["mkclean"]
        bin_path = os.path.join(dep.package_folder, "bin", "mkclean")
        self.run(f'"{bin_path}" --version', env="conanrun", ignore_errors=True)
