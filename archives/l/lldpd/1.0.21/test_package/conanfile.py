#!/usr/bin/env python3
"""Conan test_package — lldpd 1.0.21

L1 test: verify that liblldpctl is usable as a consumer library by exercising
its public connection lifecycle and error-handling API. The test runs offline —
lldpctl_new() allocates the connection handle without connecting to the daemon
socket, so no running lldpd is required.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LldpdTestConan(ConanFile):
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
        # L1 consumer test: run the binary that links and exercises liblldpctl.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lldpd"), env="conanrun")
