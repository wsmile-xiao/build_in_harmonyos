#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/physfs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PhysfsTestConan(ConanFile):
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
        # Run test binary directly with LD_LIBRARY_PATH (OHOS conanrun doesn't set it)
        dep = self.dependencies["physfs"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_physfs")
        self.run(test_bin)
