#!/usr/bin/env python3
"""Conan test_package for LightGBM 4.6.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LightGBMTestConan(ConanFile):
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
        if not can_run(self):
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_lightgbm_api"), env="conanrun")
        dep = self.dependencies["lightgbm"]
        candidates = [
            os.path.join(dep.package_folder, "bin", "lightgbm"),
            os.path.join(dep.package_folder, "bin", "lightgbm.exe"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                self.output.info(f"lightgbm CLI packaged at: {candidate}")
                return
        raise Exception(f"lightgbm binary not found in package: {', '.join(candidates)}")
