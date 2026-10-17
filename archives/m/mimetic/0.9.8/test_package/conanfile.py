#!/usr/bin/env python3
"""Conan test_package for mimetic 0.9.8 — consumer-side API verification."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MimeticTestConan(ConanFile):
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
        if not can_run(self):
            self.output.warning("交叉构建的消费者无法在构建主机上运行。")
            return
        binary = os.path.join(self.cpp.build.bindirs[0], "test_mimetic")
        self.run(f'"{binary}"', env="conanrun")
