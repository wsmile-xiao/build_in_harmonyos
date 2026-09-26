#!/usr/bin/env python3
"""tsocks consumer test: load the built shim library on the device."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class TsocksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_tsocks"),
            env="conanrun",
        )
