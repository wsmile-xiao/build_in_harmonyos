#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/ccurl/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CcurlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # curl.hh intentionally exposes cURL types in its public API. Keep the
        # header dependency explicit in this consumer so CMakeDeps supplies the
        # published CURL::libcurl include and link target on OHOS workers.
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindir, "test_ccurl"), env="conanrun")
