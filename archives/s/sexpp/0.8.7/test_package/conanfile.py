#!/usr/bin/env python3
"""Conan test_package — sexpp 0.8.7 consumer verification.

Builds a real consumer program against the packaged libsexpp and executes it
on the OHOS device (L0d: test() must actually run something).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SexppTestConan(ConanFile):
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
        # Execute the consumer binary built against the packaged library.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sexpp"),
                 env="conanrun")
