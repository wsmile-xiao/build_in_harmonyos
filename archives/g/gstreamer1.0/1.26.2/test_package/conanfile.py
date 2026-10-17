#!/usr/bin/env python3
"""Conan test_package -- gstreamer1.0 1.26.2 consumer test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

class Gstreamer1TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gstreamer1")
        self.run(bin_path, env="conanrun")
