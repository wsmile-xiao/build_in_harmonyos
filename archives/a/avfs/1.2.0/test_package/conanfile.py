#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/avfs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AvfsTestConan(ConanFile):
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
        # On OHOS, shared libraries are not in standard paths.
        # Set LD_LIBRARY_PATH to include the avfs package lib directory.
        avfs_dep = self.dependencies["avfs"]
        libdir = os.path.join(avfs_dep.package_folder, "lib")
        existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{libdir}:{existing_ld}" if existing_ld else libdir
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_avfs")
        self.run(test_bin)
