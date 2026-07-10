#!/usr/bin/env python3
"""Conan test_package for minizip 1.3.1.

Tests zip create + read round-trip using the minizip API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MinizipTestConan(ConanFile):
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
        # Conan's conanrun env doesn't set LD_LIBRARY_PATH on OHOS,
        # so we manually point it at the package's lib directory
        dep = self.dependencies["minizip"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_minizip"))
