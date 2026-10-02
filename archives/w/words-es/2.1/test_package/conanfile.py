#!/usr/bin/env python3
"""Conan consumer test for the packaged UTF-8 Spanish word list."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WordsEsTestConan(ConanFile):
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
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_words_es")
            self.run(f'"{executable}" --expect-count=56329', env="conanrun")
        else:
            self.output.info(
                "Cross build: the consumer executable was built. Use "
                "test_harmony.py with an x86_64 HarmonyOS PC emulator to run "
                "the platform-specific assertions."
            )
