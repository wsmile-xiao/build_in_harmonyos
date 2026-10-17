#!/usr/bin/env python3
"""Conan test_package — ascon-c consumer test (AEAD/hash via public API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AsconcTestConan(ConanFile):
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
        # 1) CTest executes the registered consumer test (see CMakeLists.txt:
        #    add_test(NAME test_ascon-c COMMAND test_ascon-c)).
        cmake = CMake(self)
        cmake.test()
        # 2) Explicit self.run() of the consumer binary — required by the L0d
        #    gate (test() must contain a real self.run() call, not a stub) and
        #    runs the actual consumer with the Conan runtime environment.
        test_bin = os.path.join(self.build_folder, "test_ascon-c")
        if not os.path.exists(test_bin):
            raise RuntimeError(f"consumer binary not found: {test_bin}")
        self.run(f'"{test_bin}"', env="conanrun")