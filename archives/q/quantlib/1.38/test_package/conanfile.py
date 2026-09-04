#!/usr/bin/env python3
"""Conan consumer test for QuantLib."""

import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class QuantLibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_binary = os.path.join(self.build_folder, "test_quantlib")
        self.run(f"{shlex.quote(bash)} -c {shlex.quote(shlex.quote(test_binary))}", env="conanrun")
