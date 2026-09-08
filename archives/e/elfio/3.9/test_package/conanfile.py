#!/usr/bin/env python3
"""Conan test_package for ELFIO 3.9.

L1 test: verifies the header-only library is correctly installed and usable.
Creates an ELF file, reads it back, and validates ELFIO API behavior.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ElfioTestConan(ConanFile):
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
        # Run both test executables to verify ELFIO API works:
        #  - test_elfio: consumer round-trip validation
        #  - test_harmonyos_elf: HarmonyOS special test (real OHOS aarch64 ELF + round-trip)
        for exe in ("test_elfio", "test_harmonyos_elf"):
            self.run(os.path.join(self.cpp.build.bindirs[0], exe), env="conanrun")
