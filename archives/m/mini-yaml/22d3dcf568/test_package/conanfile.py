#!/usr/bin/env python3
"""Conan test_package for mini-yaml 22d3dcf568.

The L1 consumer test: build a small program that includes "yaml/Yaml.hpp"
and calls Yaml::Parse / Node::As / Serialize (harmonyos_specific_test.cpp
mirrors the same API calls). CI runs this automatically via `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MiniyamlTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Run the binary explicitly so a non-zero exit fails the package test.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mini-yaml"), env="conanrun")