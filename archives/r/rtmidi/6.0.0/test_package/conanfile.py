#!/usr/bin/env python3
"""Conan test_package — rtmidi 6.0.0 (Conan L1 official test).

Consumer tests (C++): verifies the OHOS dummy-API fallback contract and
runs a complete dummy producer/monitor lifecycle. CI runs both automatically
via `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RtmidiTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        self.run(f'"{os.path.join(bindir, "test_rtmidi")}"', env="conanrun")
        self.run(f'"{os.path.join(bindir, "rtmidi_dummy_workflow")}"', env="conanrun")
