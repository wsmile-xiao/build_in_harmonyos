#!/usr/bin/env python3
"""Consumer test for zarchive/0.1.2.

Builds the C++ consumer test against the installed package and runs it, then
exercises the packaged command-line tool end to end through its shell test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZarchiveTestConan(ConanFile):
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
        # Library-level verdict: pack/read round trip through the API.
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_zarchive"),
                 env="conanrun")

        # Command-line verdict: the installed tool packs and extracts, and
        # every extracted file is byte-identical to its source.
        tool = os.path.join(self.dependencies["zarchive"].package_folder,
                            "bin", "zarchive")
        script = os.path.join(os.path.dirname(__file__),
                              "test_zarchive_cli.sh")
        self.run(f'sh "{script}" "{tool}"', env="conanrun")
