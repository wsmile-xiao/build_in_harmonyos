#!/usr/bin/env python3
"""Conan test_package — consumer validation for cpp-datetime-library.

Builds test.cpp against the installed package via find_package(datetime)
and runs it as a CTest case. Verifies a downstream consumer can compile,
link and run using only the published public API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CppDatetimeLibraryTestConan(ConanFile):
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
        # Fallback: run the binary directly if ctest config is unavailable
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_cpp-datetime-library")
        if os.path.exists(bin_path):
            self.run(bin_path, env="conanrun")