#!/usr/bin/env python3
"""Conan test_package — mp3info 0.8.5a.

mp3info is a CLI tool (application type). This test compiles a C test
program that runs the installed mp3info binary and verifies its output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Mp3InfoTestConan(ConanFile):
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
        # R32: only meaningful on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # R34: test substantively depends on the tested package by running
        # the installed binary. test.c calls mp3info -h and checks output.
        pkg = self.dependencies["mp3info"].package_folder
        mp3info_bin = os.path.join(pkg, "bin", "mp3info")

        # Run the compiled test binary with MP3INFO_BIN set
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mp3info")
        self.run(f'MP3INFO_BIN="{mp3info_bin}" "{test_bin}"', env="conanrun")
