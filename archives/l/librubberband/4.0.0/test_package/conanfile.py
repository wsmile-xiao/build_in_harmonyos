#!/usr/bin/env python3
"""Conan test_package for librubberband 4.0.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibrubberbandTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # Run the consumer test binary with the runtime environment
        # (shared librubberband + libsamplerate resolvable on OHOS).
        env = VirtualRunEnv(self).environment()
        self.run(
            os.path.join(self.build_folder, "test_librubberband"),
            env="conanrun",
        )
