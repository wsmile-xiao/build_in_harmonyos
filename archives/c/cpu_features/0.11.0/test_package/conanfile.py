#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/cpu_features/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CpufeaturesTestConan(ConanFile):
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
        # Run the consumer tests directly so the exit codes are visible in
        # the conan create log (R34: test() must actually execute the
        # package's consumers, not just configure/build them).
        bindir = self.cpp.build.bindirs[0]
        self.run(f"{os.path.join(bindir, 'test_cpu_features')} 1s", env="conanrun")
        self.run(f"{os.path.join(bindir, 'test_cpu_features_ohos')} 1s", env="conanrun")
