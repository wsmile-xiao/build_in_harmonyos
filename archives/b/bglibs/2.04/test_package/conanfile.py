#!/usr/bin/env python3
"""Conan test_package — bglibs 2.04 consumer test.

Builds test.c against the packaged bglibs libraries and, when running on
the target machine, executes it.  Under cross-compilation the binary is
built but not executed (the OHOS device build does execute it).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class BglibsTestConan(ConanFile):
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
            self.output.info(
                "Cross-compiling: skip running test_bglibs on the build host"
            )
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_bglibs"), env="conanrun")
