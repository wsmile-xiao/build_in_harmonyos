#!/usr/bin/env python3
"""Conan test_package for osip/5.3.2 — consumer test (L1).

Builds test.c against the packaged osip libraries and runs the consumer
binary; the binary asserts decoded SIP fields via the real libosipparser2
API and its exit code decides pass/fail.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OsipTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_osip")
        self.run(test_bin, env="conanrun")
