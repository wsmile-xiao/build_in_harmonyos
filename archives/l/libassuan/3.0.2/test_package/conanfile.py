#!/usr/bin/env python3
"""Consumer test for libassuan."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibassuanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libassuan")
        self.run(f'{bash} -c \'"{test_binary}"\'', env="conanrun")
