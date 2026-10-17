#!/usr/bin/env python3
"""Conan test_package for memsafe 0.4.0 — real consumer verification.

Exercises the public header-only API (memsafe.h): Shared/Weak/Locker with
synchronized access, verifies observable values are correctly written/read.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MemsafeTestConan(ConanFile):
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
        # Run the consumer binary directly: it calls memsafe.h public API and
        # verifies observable results (exit code + stdout "test_memsafe: OK").
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_memsafe"), env="conanrun")

