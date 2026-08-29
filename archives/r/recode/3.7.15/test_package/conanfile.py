#!/usr/bin/env python3
"""Conan consumer test for recode 3.7.15."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv


class RecodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: consumer link verified; target execution deferred")
            return
        test_bin = os.path.join(self.build_folder, "recode_consumer")
        self.run(test_bin, env="conanrun", cwd=self.build_folder)
