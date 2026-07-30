#!/usr/bin/env python3
"""Conan test_package — sound-touch homebrew (upstream 2.4.1)

L1 test: verify the SoundTouch header is available and compiles/link.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SoundTouchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        # Build the test consumer
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Run the test binary if we can execute it
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_soundtouch")
            self.run(f'"{bin_path}"', env="conanrun")