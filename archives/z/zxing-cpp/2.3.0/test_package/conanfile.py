#!/usr/bin/env python3
"""Consumer test for zxing-cpp 2.3.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZxingCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                self.build_folder
            ),
            env="conanrun",
        )
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_zxing_cpp"),
            env="conanrun",
        )
