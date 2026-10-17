#!/usr/bin/env python3
"""Conan consumer and fault-injection tests for words-fi 2.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.errors import ConanException


class WordsFiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        if not self.tested_reference_str:
            raise ConanException("words-fi test package must be run through conan create")
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["words-fi"]
        package_folder = dependency.package_folder
        for license_name in ("Copyright", "COPYING"):
            license_path = os.path.join(package_folder, "licenses", license_name)
            if not os.path.isfile(license_path) or os.path.getsize(license_path) == 0:
                raise ConanException(f"packaged license file is missing or empty: {license_path}")

        if not can_run(self):
            self.output.info(
                "Cross build: consumer compiled; test_harmony.py runs the actual AArch64 HarmonyOS scenarios."
            )
            return

        executable = os.path.join(self.cpp.build.bindirs[0], "test_words_fi")
        word_file = os.path.join(package_folder, "share", "dict", "words-fi")
        self.run(f'"{executable}" --expect-count=88328', env="conanrun")
        self.run(
            f'"{executable}" --word-list="{word_file}.missing" --expect-missing',
            env="conanrun",
        )

        if str(self.settings.os) != "OHOS":
            exit_code = self.run(
                f'"{executable}" --word-list="{word_file}" --require-ohos',
                env="conanrun",
                ignore_errors=True,
            )
            if exit_code == 0:
                raise ConanException("native non-OHOS consumer unexpectedly passed --require-ohos")
