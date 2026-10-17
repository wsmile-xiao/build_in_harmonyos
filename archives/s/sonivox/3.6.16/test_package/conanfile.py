#!/usr/bin/env python3
"""Consumer test package for sonivox — builds and runs test.c against the installed package.

The test drives the public EAS API: library configuration contract,
offline rendering of a generated Standard MIDI File through the embedded
wavetable samples (non-silent PCM output), and a negative control
(malformed input rejected by EAS_OpenFile).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

required_conan_version = ">=2.0"


class SonivoxTestConan(ConanFile):
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
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_sonivox")
        self.run(executable, env="conanrun")
