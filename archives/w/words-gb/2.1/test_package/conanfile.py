#!/usr/bin/env python3
"""Consumer and fault-injection tests for words-gb 2.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WordsGbTestConan(ConanFile):
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
            executable = os.path.join(self.cpp.build.bindirs[0], "test_words_gb")
            word_file = os.path.join(
                self.dependencies["words-gb"].package_folder,
                "share",
                "dict",
                "words-gb",
            )
            self.run(f'"{executable}" "{word_file}"', env="conanrun")
            self.run(
                f'"{executable}" --expect-missing "{word_file}.missing"',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: words-gb consumer was built; run both scenarios "
                "with the packaged word list on the HarmonyOS PC emulator."
            )
