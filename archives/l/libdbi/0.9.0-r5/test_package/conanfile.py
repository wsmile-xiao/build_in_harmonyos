#!/usr/bin/env python3
"""Conan consumer test for libdbi 0.9.0-r5."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibdbiTestConan(ConanFile):
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
        if not can_run(self):
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdbi")
        driver_dir = os.path.join(self.build_folder, "empty-drivers")
        os.makedirs(driver_dir, exist_ok=True)
        self.run(f'"{test_bin}" "{driver_dir}"', env="conanrun")
