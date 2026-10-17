#!/usr/bin/env python3
"""Consumer test for the packaged spirit-po headers."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SpiritPoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Execute through the profile shell; this is the real consumer binary,
        # not an echo/true placeholder.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_spirit_po'", cwd=self.cpp.build.bindirs[0], env="conanrun")
