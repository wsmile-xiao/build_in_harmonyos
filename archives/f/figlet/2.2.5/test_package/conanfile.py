#!/usr/bin/env python3
"""Conan test_package for figlet 2.2.5 — verify the CLI binary works.

Builds and runs test_figlet (test.c) which calls figlet via popen() to
verify version infocode and ASCII art output. R34: test substantively
depends on the tested package's binary.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FigletTestConan(ConanFile):
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
        if not can_run(self):
            return

        # Find the figlet binary from the installed package
        figlet_bin = "figlet"
        figlet_info = self.dependencies["figlet"]
        for bindir in figlet_info.cpp_info.bindirs:
            candidate = os.path.join(bindir, "figlet")
            if os.path.isfile(candidate):
                figlet_bin = candidate
                break

        # Find the font directory from the installed package
        font_dir = ""
        for resdir in figlet_info.cpp_info.resdirs:
            candidate = os.path.join(resdir, "figlet")
            if os.path.isdir(candidate):
                font_dir = candidate
                break

        # Set environment for the test binary to find figlet and fonts
        os.environ["FIGLET_BIN"] = figlet_bin
        if font_dir:
            os.environ["FIGLET_FONTDIR"] = font_dir

        # Run the compiled test binary which calls figlet via popen (R34)
        test_bin = os.path.join(self.build_folder, "test_figlet")
        self.run(test_bin, env="conanrun")
