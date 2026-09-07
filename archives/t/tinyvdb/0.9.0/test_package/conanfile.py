#!/usr/bin/env python3
"""Conan test_package for tinyvdb 0.9.0 — real consumer of the packaged API."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run
import os


class TinyvdbTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_tinyvdb_ops")
            self.run(f'"{bin_path}"', env="conanrun")
        else:
            self.output.info("Cross-building: test_tinyvdb_ops skipped at test time")
