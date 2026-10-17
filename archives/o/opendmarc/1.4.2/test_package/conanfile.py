#!/usr/bin/env python3
"""Conan test_package for opendmarc 1.4.2.

The consumer test links against libopendmarc and calls the DMARC record
parser API (see test.c).  CI runs this via `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpendmarcTestConan(ConanFile):
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
        # R34: run the binary that exercises libopendmarc's parser API.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_opendmarc")
        self.run(bin_path, env="conanrun")
