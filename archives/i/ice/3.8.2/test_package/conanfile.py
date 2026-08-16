#!/usr/bin/env python3
"""Conan test_package for the ZeroC Ice 3.8.2 package.

Builds a small C++ consumer that links against libIce and exercises the Ice
runtime API (Communicator + property round-trip), then runs it with the
dependency run environment (LD_LIBRARY_PATH includes the package lib dir).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IceTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ice")
        self.run(test_bin, env="conanrun")
