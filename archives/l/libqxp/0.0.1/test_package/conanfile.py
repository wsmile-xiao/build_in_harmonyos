#!/usr/bin/env python3
"""Conan test_package — libqxp 0.0.1 L1 smoke test.

Verifies that the libqxp library is correctly installed and its API
symbols (QXPDocument::isSupported) can be resolved at link time.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibqxpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("librevenge/0.0.5@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
