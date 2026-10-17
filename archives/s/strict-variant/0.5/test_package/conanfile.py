#!/usr/bin/env python3
"""Conan consumer test for strict-variant 0.5."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class StrictVariantTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Consumer executable was compiled but not run because "
                "can_run(self) is false in this environment."
            )
            return

        binary = os.path.join(self.build_folder, "strict_variant_consumer")
        if not os.path.isfile(binary):
            raise ConanException(f"Consumer test binary not found: {binary}")
        self.run(binary, env="conanrun")
