#!/usr/bin/env python3
"""Conan test_package for snow 20130616 — L1 roundtrip test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class SnowTestConan(ConanFile):
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
        if cross_building(self):
            return
        # Run the compiled test_snow binary which performs
        # embed -> extract -> verify roundtrip via system("snow ...").
        # conanrun env puts snow on PATH.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_snow"),
                 env="conanrun")
