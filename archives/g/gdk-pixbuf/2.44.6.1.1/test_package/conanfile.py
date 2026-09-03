#!/usr/bin/env python3
"""Conan test_package for gdk-pixbuf 2.44.6.1.1.

Consumer-side validation (R34): builds a small program that calls the real
gdk-pixbuf public API (gdk_pixbuf_new / gdk_pixbuf_get_width / ...) and runs
it against the packaged library.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GdkpixbufTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gdk-pixbuf")
        self.run(bin_path, env="conanrun")
