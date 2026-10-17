#!/usr/bin/env python3
"""Conan test_package for pnscan — consumer-side behaviour test.

pnscan is a scanner application: the consumer test drives the packaged
binaries the way an upstream check does — start t_listen (echo daemon,
prints its port), then scan it with pnscan -r "Hello" and assert the
"Hello, World!" banner is reported.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PnscanTestConan(ConanFile):
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
        dep = self.dependencies["pnscan"]
        bindir = os.path.join(dep.package_folder, "bin")
        consumer = os.path.join(self.cpp.build.bindirs[0], "dd_consumer")
        self.run(f'PNSCAN_BIN="{bindir}" "{consumer}"')
