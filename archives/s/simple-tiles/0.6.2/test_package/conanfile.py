#!/usr/bin/env python3
"""Conan test_package — simple-tiles 0.6.2

Consumer check (aligned with Homebrew formula test): simplet_map_new/free.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class SimpleTilesTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: compile/link only")
            return
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_simple_tiles")
            ret = self.run(f'"{bin_path}"', env="conanrun")
            assert ret == 0, f"test_simple_tiles failed with exit code {ret}"
