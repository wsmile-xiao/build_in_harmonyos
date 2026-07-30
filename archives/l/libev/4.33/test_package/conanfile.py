#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libev/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-build detected; target execution skipped")
            return
        cmake = CMake(self)
        cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libev")
        self.run(test_bin, env="conanrun", cwd=self.build_folder)
