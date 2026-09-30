#!/usr/bin/env python3
"""Consumer and fault-injection tests for words-it 2.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WordsItTestConan(ConanFile):
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
            self.output.info(
                "Cross build: words-it consumers were built; run the list and "
                "HarmonyOS environment checks on an AArch64 HarmonyOS device."
            )
            return

        executable = os.path.join(self.cpp.build.bindirs[0], "test_words_it")
        word_file = os.path.join(
            self.dependencies["words-it"].package_folder,
            "share",
            "dict",
            "words-it",
        )
        self.run(f'"{executable}"', env="conanrun")
        self.run(
            f'"{executable}" --expect-missing "{word_file}.missing"',
            env="conanrun",
        )

        if str(self.settings.os) == "OHOS":
            ohos_executable = os.path.join(
                self.cpp.build.bindirs[0], "test_words_it_ohos"
            )
            self.run(f'"{ohos_executable}"', env="conanrun")
