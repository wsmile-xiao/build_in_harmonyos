#!/usr/bin/env python3
"""Conan consumer test for svgpp/1.3.1 (layer 2 of docs/TEST_QUALITY_SPEC.md).

Builds a real consumer program against the installed headers and runs it:
test_svgpp.cpp instantiates svgpp::path_data_grammar and
svgpp::transform_grammar and checks the parsed geometry, so the test fails if
the package ships incomplete headers or loses its Boost include paths.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SvgppTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_svgpp"),
                 env="conanrun")
