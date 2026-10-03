#!/usr/bin/env python3
"""Conan test_package — libcorrect 0.0-git20260204 consumer verification.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libcorrect/0.0-git20260204/test_package/conanfile.py
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibcorrectTestConan(ConanFile):
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
        # ctest runs both consumers (test_correct + test_correct_ohos);
        # the explicit self.run() below re-executes each binary directly
        # so the log carries unambiguous run evidence.
        cmake = CMake(self)
        cmake.test()
        bindir = self.cpp.build.bindirs[0]
        self.run(f"{bindir}/test_correct", env="conanrun")
        self.run(f"{bindir}/test_correct_ohos", env="conanrun")
