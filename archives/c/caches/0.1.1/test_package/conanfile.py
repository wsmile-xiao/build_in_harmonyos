#!/usr/bin/env python3
"""Conan test_package for caches 0.1.1

Consumer-side test verifying the header-only cache library works on
HarmonyOS (aarch64-linux-ohos). CI runs this automatically via
`conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CachesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_caches"), env="conanrun")
        self.run(os.path.join(bin_dir, "test_caches_ohos"), env="conanrun")
