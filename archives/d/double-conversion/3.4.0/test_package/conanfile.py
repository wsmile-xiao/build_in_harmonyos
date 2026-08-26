#!/usr/bin/env python3
"""Conan test_package for double-conversion 3.4.0.

L1 test: Verifies the package can be consumed and the library works correctly.
CI runs this automatically via `conan create` (which invokes test_package).

R33: compiler paths come from Conan profile, no shell env vars.
R34: test() calls self.run() to execute the test binary (not a stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DoubleConversionTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} -c './test_double-conversion'", env="conanrun")
