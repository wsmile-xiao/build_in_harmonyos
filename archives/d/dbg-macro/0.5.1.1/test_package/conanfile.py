#!/usr/bin/env python3
"""Conan test_package for dbg-macro 0.5.1.1 (upstream 0.5.1)."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DbgMacroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
            self.output.warning(
                "cross-building: consumer executable compiled but not executed"
            )
            return

        bin_path = os.path.join(self.cpp.build.bindir, "test_dbg_macro")
        if not os.path.isfile(bin_path):
            raise ConanException(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
