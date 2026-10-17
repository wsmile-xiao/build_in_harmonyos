#!/usr/bin/env python3
"""Conan test_package — ayatana-common 0.9.11 L1 test.

Compiles and runs a C program that calls the real ayatana-common API
(desktop-session detection + have_program), verifying headers, linking and
runtime behaviour.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AyatanaCommonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_ayatana_common" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
