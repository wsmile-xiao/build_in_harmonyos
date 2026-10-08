#!/usr/bin/env python3
"""Conan test_package for lss (header-only).

R34: This test actually includes and uses linux_syscall_support.h,
calling sys_getpid() and sys_close() to verify the library works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LssTestConan(ConanFile):
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
        # Run the test executable directly (no CTest needed)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_lss")
        self.run(exe, env="conanrun")
