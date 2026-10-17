#!/usr/bin/env python3
"""Test package for irssi — builds and runs a test that verifies the irssi binary.

R34: the test compiles a C program that calls irssi --version via popen(),
captures the output, and verifies the version string is present.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IrssiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            self.output.info("Skipping runtime tests while cross-building")
            return

        # Run the compiled test which calls irssi --version via popen()
        self.run(os.path.join(self.build_folder, "test_irssi"), env="conanrun")
