#!/usr/bin/env python3
"""Conan test_package for epsilon — verifies the library API.

This test calls eps_get_fb_info() and checks the wavelet filterbank list,
ensuring the epsilon library is properly linked and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EpsilonTestConan(ConanFile):
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
        # Run the test binary directly to verify the epsilon library API
        # (R34: test must exercise the tested package's API)
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_epsilon")
        self.run(cmd, env="conanrun")
