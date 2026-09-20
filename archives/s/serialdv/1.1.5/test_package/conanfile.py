#!/usr/bin/env python3
"""Conan test_package for serialdv — consumer-perspective L1 test.

Links the packaged libserialdv.so and runs the consumer regression test;
`conan create` executes this automatically (CI L1a checks the trace).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SerialDvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_serialdv")
        self.run(executable, env="conanrun")
