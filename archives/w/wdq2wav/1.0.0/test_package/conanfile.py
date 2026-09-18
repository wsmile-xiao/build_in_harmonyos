#!/usr/bin/env python3
"""Conan test_package for wdq2wav."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Wdq2wavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_wdq2wav")
        self.run(test_binary, env="conanrun")