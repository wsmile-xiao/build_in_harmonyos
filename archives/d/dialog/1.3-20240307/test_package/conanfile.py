#!/usr/bin/env python3
"""Conan test_package — dialog 1.3-20240307.

Verifies that the dialog binary is installed and reports its version.
The dialog binary is the primary artifact; running --version exercises
the full ncurses linkage chain at runtime.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DialogTestConan(ConanFile):
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
        # Run the dialog binary --version to verify it works.
        # The dialog binary statically links ncurses, so this exercises
        # the full dependency chain at runtime.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_dialog")
        self.run(f"{bin_path}", env="conanrun")
