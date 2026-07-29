#!/usr/bin/env python3
"""Consumer and fault-injection tests for hunspell-ca 3.0.91."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class HunspellCaTestConan(ConanFile):
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
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_hunspell_ca"
            )
            dictionary_dir = os.path.join(
                self.dependencies["hunspell-ca"].package_folder,
                "share",
                "hunspell",
            )
            self.run(f'"{executable}" "{dictionary_dir}"', env="conanrun")
            self.run(
                f'"{executable}" --expect-missing '
                f'"{dictionary_dir}.missing"',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: hunspell-ca consumer was built; run both "
                "scenarios with the dictionaries on the HarmonyOS PC emulator."
            )
