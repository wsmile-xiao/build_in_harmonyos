#!/usr/bin/env python3
"""Conan test_package -- gst-plugins-base 1.28.3 consumer test.

Verifies that gst-plugins-base libraries (pbutils, audio, video)
can be found and their APIs work correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstPluginsBaseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_base")
        self.run(bin_path, env="conanrun")
