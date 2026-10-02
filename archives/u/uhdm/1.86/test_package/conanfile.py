#!/usr/bin/env python3
"""Conan test_package for uhdm — L1 consumer test.

CI runs this via `conan create`. Verifies:
  1. libuhdm links and the VPI API roundtrips (test.cpp, via ctest).
  2. A shipped CLI tool (uhdm-dump) executes from the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UhdmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv: the shipped tools (uhdm-*) link libuhdm.so without an
    # install RPATH; the run env provides LD_LIBRARY_PATH to the package lib
    # dir at test time (Conan-managed dependency chain).
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
        cmake = CMake(self)
        cmake.test()
        # R34/PF3: a shipped CLI tool must execute. `uhdm-dump` with no args
        # prints its usage and exits 0 (verified on OHOS aarch64).
        self.run(
            f'"{os.path.join(self.dependencies["uhdm"].cpp_info.bindirs[0], "uhdm-dump")}"',
            env="conanrun",
        )
