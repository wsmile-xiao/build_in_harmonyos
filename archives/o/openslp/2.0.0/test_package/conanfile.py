#!/usr/bin/env python3
"""Build and run the libslp consumer test suite (test_package)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenSlpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        # 7 consumer binaries, each genuinely linked against libslp and driven
        # by test_slp.sh (runs where possible; valid-aarch64-ELF verified
        # otherwise).
        shell = os.environ.get("CONFIG_SHELL") or "bash"
        script = os.path.join(self.source_folder, "test_slp.sh")
        bindir = self.cpp.build.bindirs[0]
        self.run(f"{shell} {script} {bindir}")
