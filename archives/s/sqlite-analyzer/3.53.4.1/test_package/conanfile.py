#!/usr/bin/env python3
"""Test package — sqlite-analyzer 3.53.4.1 (CMake)"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

class TestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sqlite/3.53.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.build_folder, "test_package"), env="conanrun")
        analyzer_bin = os.path.join(self.dependencies["sqlite-analyzer"].package_folder, "bin", "sqlite3_analyzer")
        self.run(f'"{analyzer_bin}" test_analyzer.db', cwd=self.build_folder, env="conanrun")
