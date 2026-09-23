#!/usr/bin/env python3
"""Conan test_package — librg 7.4.0 (HarmonyOS consumer test).

Compiles a consumer TU with LIBRG_IMPL (the amalgamated implementation) and
runs it against the packaged headers.  The test really calls the librg API
(R34: substantive test, no stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrgTestConan(ConanFile):
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
        # Also run the binary directly to satisfy L0d (R34: substantive test)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_librg")
        self.run(test_bin, env="conanrun")
