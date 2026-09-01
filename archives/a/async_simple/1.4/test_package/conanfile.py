#!/usr/bin/env python3
"""Conan test_package — async_simple 1.4

L1 test: verify the packaged library can be found, linked, and executed.
Calls async_simple coroutine API to verify C++20 coroutine support.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AsyncSimpleTestConan(ConanFile):
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
        dep = self.dependencies["async_simple"]
        dep_libdir = os.path.join(dep.package_folder, "lib")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_async_simple")
        self.run(
            f'export LD_LIBRARY_PATH="{dep_libdir}:$LD_LIBRARY_PATH"; {bin_path}',
            env="conanrun",
        )
