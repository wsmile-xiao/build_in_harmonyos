#!/usr/bin/env python3
"""Conan test_package — mksh 59c

Tests that the mksh binary can be executed and reports its version.
mksh is a shell binary, not a library.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MkshTestConan(ConanFile):
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
        # Run the mksh binary to verify it works
        mksh_bin = os.path.join(self.dependencies["mksh"].package_folder, "bin", "mksh")
        self.run(f"{mksh_bin} -c 'echo $KSH_VERSION'")
