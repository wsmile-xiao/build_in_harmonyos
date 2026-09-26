#!/usr/bin/env python3
"""Conan test_package for microlog 7.1.0 (CMake consumer test).

L1 test in the five-level test system; CI runs it via `conan create`.
Consumes the installed microlog package through find_package(microlog CONFIG)
and verifies observable stdout output from the public ulog_info() macro.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MicrologTestConan(ConanFile):
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
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_microlog')}", env="conanrun")
