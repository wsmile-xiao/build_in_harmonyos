#!/usr/bin/env python3
"""Conan test_package — llhttp 9.3.1 consumer test.

L1 test: verifies that the llhttp package can be consumed by a downstream
project. The test links against libllhttp and calls core API functions
to parse a simple HTTP request.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LlhttpTestConan(ConanFile):
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
        # Conan 2.x: use cpp.build.bindirs[0] for executable location
        # On OHOS, conanrun env may not set LD_LIBRARY_PATH, so add it manually
        dep = self.dependencies["llhttp"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        os.environ["LD_LIBRARY_PATH"] = libdir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_llhttp"), env="conanrun")
