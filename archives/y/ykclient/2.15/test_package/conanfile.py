#!/usr/bin/env python3
"""test_package for ykclient — compiles consumer_test.c against the packaged
library and runs it (real API calls + hard assertions, fully offline)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class YkclientTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Run the consumer binary directly as well: it exits non-zero when any
        # assertion fails. conanrun makes the dependency shared objects visible
        # (musl ignores DT_RUNPATH).
        exe = os.path.join(self.build_folder, "consumer_test")
        if not os.path.exists(exe):
            exe = os.path.join(self.build_folder, "Release", "consumer_test")
        self.run(f'"{exe}"', env="conanrun")
