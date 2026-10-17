#!/usr/bin/env python3
"""Conan test_package — buddy_alloc 1.3.2.

Two executables are built against the INSTALLED package (public header only):
  1. test_consumer      — consumer use case: business-upper-layer style app that
     uses only buddy_alloc's public API through the exported header + CMake
     target (normal link path). Verifies alloc/free/alloc_size with observable
     output (R34 / consumer hard gate).
  2. test_ohos          — HarmonyOS-specific validation: 64-byte aligned arena,
     embed mode, resize semantics, safe-free protection, large-arena behavior.
     Distinct from upstream tests.c cases (assertions added for this platform).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BuddyAllocTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        self.run(f"{self.cpp.build.bindirs[0]}/test_consumer", env="conanrun")
        self.run(f"{self.cpp.build.bindirs[0]}/test_ohos", env="conanrun")
