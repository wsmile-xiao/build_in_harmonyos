#!/usr/bin/env python3
"""Conan test_package for far2l 2.8.0.

Verifies the far2l binary is functional by:
  1. Running the compiled test_far2l binary (ELF checks from .cpp)
  2. Running test_far2l.sh (ELF format + --help output + TTY headless)

This satisfies R34/L0d/L1e: explicit self.run() with real binary execution.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Far2lTestConan(ConanFile):
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
        far2l_bin = os.path.join(
            self.dependencies["far2l"].package_folder, "bin", "far2l"
        )

        # FR5: use SHELL env or PATH lookup instead of hardcoded device path
        bash = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or shutil.which("bash") or "bash"

        # FR1: execute the compiled test_far2l binary (runs 13 CHECK assertions from .cpp)
        test_cpp_bin = os.path.join(self.build_folder, "test_far2l")
        self.run(test_cpp_bin + " " + far2l_bin, env="conanrun")

        # Execute test_far2l.sh (runs 6 shell test blocks including TTY headless)
        test_script = os.path.join(self.source_folder, "test_far2l.sh")
        self.run(bash + " " + test_script + " " + far2l_bin, env="conanrun")
