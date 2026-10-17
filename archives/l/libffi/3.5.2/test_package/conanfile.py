#!/usr/bin/env python3
"""Installed-package consumer test for libffi 3.5.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibffiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
                "NOT_RUN LIBFFI_TARGET_CONSUMER=0/1 reason=cross_building"
            )
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "libffi_consumer" + suffix
        )
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
