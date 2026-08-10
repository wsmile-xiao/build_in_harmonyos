#!/usr/bin/env python3
"""Test package for pciutils 3.13.0 — verifies libpci API (pci_alloc/pci_cleanup)"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PciutilsTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pciutils")
        self.run(test_bin, env="conanrun")
