#!/usr/bin/env python3
"""Conan test_package — midifile g20200602 (Conan L1 official test).

Consumer test (C++): SMF binary write/read roundtrip (track/event/pitch
survival) + doTimeAnalysis seconds sanity against the packaged static lib.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MidifileTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_midifile")
        self.run(f'"{exe}"', env="conanrun")
