#!/usr/bin/env python3
"""Conan test_package — epr-api 2.3 consumer test.

Uses VirtualRunEnv + explicit self.run(env='conanrun') instead of cmake.test():
CTest does not apply the conanrun environment, so a package-provided shared
library (libepr_api.so.3) would not be found at runtime (knowledge E298).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EprapiTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_epr-api")
        self.run(f'"{test_bin}"', env="conanrun", cwd=self.build_folder)
