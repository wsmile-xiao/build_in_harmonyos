#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for cmake/4.3.4.

Runs a real smoke test: the packaged cmake must configure + build a tiny
project and the built binary must run (see test.c). The test binary is
invoked directly (not via cmake.test()) because the make jobserver
deadlocks on this platform under nested conan->make invocations; the
project itself builds with the Ninja generator for the same reason.
"""
import os
import platform

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CmakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        CMakeToolchain(self, generator="Ninja").generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_cmake")
        if platform.system() == "Windows":
            exe += ".exe"
        # Path of the packaged cmake binary inside the dependency package
        cmake_cpp_info = self.dependencies["ccmake"].cpp_info
        pkg_cmake = os.path.join(cmake_cpp_info.bindirs[0], "cmake")
        if platform.system() == "Windows":
            pkg_cmake += ".exe"
        self.run(f'"{exe}" "{pkg_cmake}"', env="conanrun")
