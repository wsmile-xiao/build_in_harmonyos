#!/usr/bin/env python3
"""Conan test_package — libevent 2.1.12

L1 test: verify the package can be found, linked, and the library API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibeventTestConan(ConanFile):
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
        # Run the test binary with LD_LIBRARY_PATH set to the package's lib dir
        # VirtualRunEnv doesn't properly set LD_LIBRARY_PATH on OHOS
        lib_dir = os.path.join(self.dependencies["libevent"].package_folder, "lib")
        cmd = os.path.join(self.cpp.build.bindir, "test_libevent")
        self.run(f"LD_LIBRARY_PATH={lib_dir}:$LD_LIBRARY_PATH {cmd}")
