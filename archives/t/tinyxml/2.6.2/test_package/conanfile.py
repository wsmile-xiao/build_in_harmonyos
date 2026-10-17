#!/usr/bin/env python3
"""Conan consumer test for TinyXML."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TinyxmlTestConan(ConanFile):
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
            self.output.warning("Cross-built tinyxml consumer cannot run on this host")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "tinyxml_consumer")
        self.run(executable, env="conanrun")
