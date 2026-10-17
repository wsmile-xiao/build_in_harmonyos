#!/usr/bin/env python3
"""Conan test package for falcosecurity-libs CMake consumers."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class FalcoSecurityLibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        dependency = self.dependencies["falcosecurity-libs"]
        package_lib = os.path.join(dependency.package_folder, "lib")
        bundled_lib = os.path.join(package_lib, "falcosecurity")
        toolchain.cache_variables["CMAKE_BUILD_RPATH"] = f"{package_lib};{bundled_lib}"
        toolchain.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"-Wl,-rpath,{package_lib}"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = self.cpp.build.bindirs[0] + "/test_falcosecurity_libs"
            self.run(f'"{executable}"', env="conanrun")
