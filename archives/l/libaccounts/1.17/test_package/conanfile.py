#!/usr/bin/env python3
"""Conan test_package — libaccounts 1.17 (upstream: libaccounts-glib).

Verifies the package can be linked and that the core GObject types
(AgManager, AgAccountService) are registered after library init.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibAccountsTestConan(ConanFile):
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
        # Run the test binary directly to verify the library is functional
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libaccounts"),
                 env="conanrun")
