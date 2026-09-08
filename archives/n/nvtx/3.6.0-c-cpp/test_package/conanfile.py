#!/usr/bin/env python3
"""Conan test_package for nvtx 3.6.0-c-cpp.

Builds and runs a consumer executable, test_nvtx, that:
  1. Uses the nvtx3 C++ header API (nvtx3::scoped_range) — upstream public API
  2. Links the packaged static lib nvtxw3-loader and calls nvtxwLoad /
     nvtxwUnload against a non-existent backend (verifies the loader's
     dlopen/dlsym path returns NVTXW_RESULT_LIBRARY_NOT_FOUND gracefully)

On HarmonyOS the dlopen/dlsym path is exercised through the loader library
compiled against the OHOS SDK, giving a real platform-specific check (R40).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NvtxTestConan(ConanFile):
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
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_nvtx"), env="conanrun")