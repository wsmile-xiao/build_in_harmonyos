#!/usr/bin/env python3
"""Consumer test for gdk-pixbuf 2.44.6."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GdkPixbufTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(
            self.cpp.build.bindirs[0], "test_gdk_pixbuf"
        )
        if can_run(self):
            self.run(test_binary, env="conanrun")
        else:
            self.output.info("Cross-building: consumer binary is run on OHOS device")
