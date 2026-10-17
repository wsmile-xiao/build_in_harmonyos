#!/usr/bin/env python3
"""Conan test_package for Boost 1.90.0.4 compiled components and headers."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BoostCompiledTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping Boost compiled component runtime test while cross-building")
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        test_binary = os.path.join(self.cpp.build.bindirs[0], f"test_boost_compiled{suffix}")
        self.run(f'"{test_binary}" --name ohos --count 3', cwd=self.build_folder, env="conanrun")
