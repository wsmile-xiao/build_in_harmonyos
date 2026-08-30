#!/usr/bin/env python3
"""Conan test_package — cista 0.16 (header-only C++ serialization & reflection).

Consumer-side verification: compiles against the packaged headers and performs
a serialization/deserialization roundtrip (R34: substantive dependency on the
tested package's API).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class CistaTestConan(ConanFile):
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
        if cross_building(self):
            # Cross to aarch64-linux-ohos: binary cannot run on the build host.
            # Upstream test suite was cross-compiled separately as compile evidence.
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cista"), env="conanrun")