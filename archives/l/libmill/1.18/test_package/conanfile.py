#!/usr/bin/env python3
"""Conan test_package — libmill 1.18 consumer test.

Builds a C consumer against the installed libmill and runs it.  The consumer
drives coroutines, unbuffered/buffered channels and the scheduler clock through
the public <libmill.h> API (see src/test_libmill.c), so a package that links
but does not work cannot pass.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmillTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libmill")
        self.run(test_bin, env="conanrun")
