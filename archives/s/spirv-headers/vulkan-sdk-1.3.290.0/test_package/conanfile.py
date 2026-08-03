#!/usr/bin/env python3
"""Conan test package for SPIRV-Headers."""

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if cross_building(self):
            self.output.info(
                "Cross-building: SPIR-V C/C++ public API compile tests passed"
            )
            return
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
