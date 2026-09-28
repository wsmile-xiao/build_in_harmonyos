#!/usr/bin/env python3
"""Conan test_package for libuhttpd 3.14.2.

L1 consumer test: builds a functional HTTP round-trip test against the
installed libuhttpd + libev, verifying the library actually serves a request
(R34: the test must use the package API, not print-only).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibuhttpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # uhttpd.h includes <ev.h>, so the consumer needs libev headers at
        # compile time; declare it explicitly like the netatalk precedent.
        self.requires("libev/4.33")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libuhttpd"), env="conanrun")
