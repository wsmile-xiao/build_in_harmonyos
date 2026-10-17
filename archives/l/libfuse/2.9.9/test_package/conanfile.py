#!/usr/bin/env python3
"""Conan test_package for libfuse 2.9.9.

R34: test_package must actually call the tested package's API.
This test calls fuse_version() to verify the library links and the
symbol is available. It does not attempt to mount (OHOS cannot mount
FUSE without kernel module + permissions).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfuseTestConan(ConanFile):
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
        # R34: run the test binary which calls libfuse's fuse_version() API.
        # fuse_version() returns the FUSE API version (e.g. 26 for 2.9.9).
        bin_path = os.path.join(self.cpp.build.bindir, "test_libfuse")
        self.run(f'"{bin_path}"', env="conanrun")
