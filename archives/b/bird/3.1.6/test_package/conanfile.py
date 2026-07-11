#!/usr/bin/env python3
"""Conan test_package for BIRD 3.1.6 — L2 smoke test.

Builds a C test program that calls `bird --version` via system()
to verify the installed binary is functional.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BirdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        dep = self.dependencies["bird"]
        if dep.cpp_info.bindirs:
            bird_path = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "bird")
            tc.variables["BIRD_BIN_PATH"] = bird_path
        tc.generate()

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run("ctest --output-on-failure", env="conanrun")
