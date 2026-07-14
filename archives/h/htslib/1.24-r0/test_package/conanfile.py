#!/usr/bin/env python3
"""Conan test_package — htslib/1.24-r0 consumer test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HtslibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain):
            with open(toolchain, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("/data/service/hnp/bin/clang++", "clang++")
            content = content.replace("/data/service/hnp/bin/clang", "clang")
            with open(toolchain, "w", encoding="utf-8") as f:
                f.write(content)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": "clang", "CMAKE_CXX_COMPILER": "clang++"})
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_htslib"), env="conanrun")
