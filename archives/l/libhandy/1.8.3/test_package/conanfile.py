#!/usr/bin/env python3
"""Consumer test for libhandy 1.8.3."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibhandyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libhandy")
        if os.path.isfile(bin_path):
            self.run(bin_path, env="conanrun")
