#!/usr/bin/env python3
"""Conan test_package for libffi 3.4.4 — L1 smoke test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibffiTestConan(ConanFile):
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
        # Explicitly set LD_LIBRARY_PATH for shared lib loading on OHOS
        libdir = os.path.join(self.dependencies["libffi"].package_folder, "lib")
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libffi")
        self.run(f"LD_LIBRARY_PATH={libdir} {cmd}")
