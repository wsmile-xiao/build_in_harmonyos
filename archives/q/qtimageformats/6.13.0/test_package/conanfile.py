#!/usr/bin/env python3
"""Consume qtimageformats through Qt6::Gui and run the plugin assertions."""

import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class QtimageformatsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # NOTE: default implicit test_type (no "explicit") so that `conan create`
    # in CI actually runs test(); an explicit test_type would skip it.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.presets_build_environment = build_env.environment()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(shlex.join([
                os.path.join(self.cpp.build.bindirs[0], "test_qtimageformats")
            ]), env="conanrun")
