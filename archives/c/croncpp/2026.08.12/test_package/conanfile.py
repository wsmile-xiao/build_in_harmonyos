#!/usr/bin/env python3
"""Conan test_package for croncpp — L1 consumer test.

Compiles a consumer against croncpp::croncpp via CMakeDeps and runs it on the
target host (HarmonyOS aarch64). The test exercises real library behavior:
cron expression parsing, next-occurrence computation with deterministic
expected values, traits dialects (standard/quartz), invalid-expression
rejection, and the chrono/time_t overloads on the OHOS libc.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CroncppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_croncpp_ohos")
        self.run(f'"{test_bin}"', env="conanrun")
