#!/usr/bin/env python3
"""Conan test_package — libpopcnt 2.0 (header-only bit population count).

Consumer-side verification (R34): compiles against the packaged `libpopcnt.h`
and runs real `popcnt()` API calls, verifying known bit counts for crafted
inputs and large arrays (POPCNT/AVX2/NEON code paths).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class LibpopcntTestConan(ConanFile):
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
        for exe in ("test_libpopcnt", "test_libpopcnt_hmos"):
            bin_path = os.path.join(self.cpp.build.bindirs[0], exe)
            self.run(bin_path, env="conanrun")
