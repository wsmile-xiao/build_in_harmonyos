#!/usr/bin/env python3
"""Conan test_package - flatbuffers 25.12.19.

Consumer test: compiles and calls the real library API (FlatBufferBuilder,
Vector read-back and flexbuffers map round trip) and additionally runs the
packaged flatc tool asserting its version output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class FlatbuffersTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        dep = self.dependencies["flatbuffers"]
        if dep.options.flatc:
            flatc = os.path.join(dep.cpp_info.bindirs[0], "flatc")
            version = self.tested_reference_str.split("/")[1].split("@")[0].split("#")[0]
            self.run(
                f'{flatc} --version | grep "flatc version {version}"',
                env="conanrun",
            )
