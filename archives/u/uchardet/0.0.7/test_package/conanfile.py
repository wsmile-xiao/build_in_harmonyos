#!/usr/bin/env python3
"""Conan test_package — uchardet 0.0.7 consumer test (L1, R34).

Builds test.c against the installed uchardet package via CMakeDeps and
runs it directly: the test feeds ASCII / UTF-8 / GB18030 / BIG5 byte
sequences through the public C API and asserts the detected charset
names (samples pre-verified with the upstream CLI on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UchardetTestConan(ConanFile):
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
        # R34: actually execute the consumer test binary; non-zero exit
        # (any detection mismatch) fails the package.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_uchardet")
        self.run(f'"{exe}"', env="conanrun")
