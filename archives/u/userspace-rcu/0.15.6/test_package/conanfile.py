#!/usr/bin/env python3
"""test_package for userspace-rcu 0.15.6 — library API smoke test (R34).

Verifies that the consumer can link against liburcu and call the RCU API.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class UserspaceRcuTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_userspace_rcu")
            self.run(bin_path, env="conanrun")
