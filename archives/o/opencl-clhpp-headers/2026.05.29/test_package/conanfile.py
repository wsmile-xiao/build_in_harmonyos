#!/usr/bin/env python3
"""Conan test_package — opencl-clhpp-headers 2026.05.29

Verifies the C++ OpenCL header can be included and compiled.
Uses CMake OBJECT library (compile-only, no linking) because CL/opencl.hpp
template destructors reference OpenCL API symbols requiring the ICD loader.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenclClhppHeadersTestConan(ConanFile):
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
        # Verify the compiled object file exists (compilation succeeded = header valid)
        # Also verify the header files are present in the package
        clhpp_pkg = self.dependencies["opencl-clhpp-headers"]
        header_path = os.path.join(clhpp_pkg.package_folder, "include", "CL", "opencl.hpp")
        cl2_path = os.path.join(clhpp_pkg.package_folder, "include", "CL", "cl2.hpp")
        self.run(f"test -f '{header_path}' -a -f '{cl2_path}'")
