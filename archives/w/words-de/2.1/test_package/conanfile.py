#!/usr/bin/env python3
"""Consumer and fault-injection tests for words-de 2.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WordsDeTestConan(ConanFile):
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
        executable = os.path.join(self.cpp.build.bindirs[0], "test_words_de")
        package = self.dependencies["words-de"].package_folder
        dictionary_dir = os.path.join(package, "share", "dict")
        if can_run(self):
            self.run(f'"{executable}" "{dictionary_dir}"', env="conanrun")
            self.run(
                f'"{executable}" --expect-missing "{dictionary_dir}\\missing"',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: words-de consumer was built; run it on a matching "
                "target runtime when hardware is available."
            )
