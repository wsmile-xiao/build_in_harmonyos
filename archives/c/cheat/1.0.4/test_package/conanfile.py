#!/usr/bin/env python3
"""Conan test_package — cheat 1.0.4.

Consumer test: builds a C program that includes <cheat.h> and defines real
CHEAT_TEST cases with cheat_assert / cheat_assert_not / cheat_assert_int,
then runs it. Each failing assertion makes the binary exit non-zero.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class CheatTestConan(ConanFile):
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
        if can_run(self):
            for name in ("test_cheat", "test_ohos"):
                bin_path = os.path.join(self.cpp.build.bindirs[0], name)
                if not os.path.isfile(bin_path):
                    raise Exception(f"Test binary not found: {bin_path}")
                self.run(bin_path, env="conanrun")
