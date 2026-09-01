#!/usr/bin/env python3
"""Conan test_package for boost-di 1.3.2 — header-only consumer smoke test.

Builds test_di.cpp (real Boost.DI API: make_injector/bind/create) with CMake
and runs it (R34: test must substantively depend on the tested package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostDiTestConan(ConanFile):
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
        # L0d/L1: also run the consumer binary directly for runtime verification
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_boost_di"),
                 env="conanrun")
