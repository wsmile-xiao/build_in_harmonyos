#!/usr/bin/env python3
"""Conan test_package — libfreenect 0.5.3 (Conan L1 smoke test)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibfreenectTestConan(ConanFile):
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
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_freenect", "test_sync", "test_harmony"):
            self.run(os.path.join(bindir, exe), env="conanrun")
