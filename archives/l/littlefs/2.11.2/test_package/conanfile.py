#!/usr/bin/env python3
"""Conan test_package — littlefs 2.11.2 L1 test.

R34: test_package source calls the packaged API for real — the test
formats/mounts a littlefs image on an in-memory block device, creates
files, writes/reads back data and verifies it (non-empty shell-free test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LittlefsTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_littlefs")
        self.run(f"\"{test_bin}\"", env="conanrun")
