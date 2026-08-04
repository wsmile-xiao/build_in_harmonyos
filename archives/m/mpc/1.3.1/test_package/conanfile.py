#!/usr/bin/env python3
"""Conan test_package for GNU MPC 1.3.1."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MpcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        include_dirs = []
        for dep_name in ("gmp", "mpfr"):
            include_dir = os.path.join(
                self.dependencies[dep_name].package_folder, "include"
            )
            if os.path.isdir(include_dir):
                include_dirs.append(include_dir)

        tc = CMakeToolchain(self)
        tc.variables["MPC_TEST_DEP_INCLUDE_DIRS"] = ";".join(include_dirs)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        bin_path = os.path.join(self.cpp.build.bindir, "test_mpc")
        self.run(bin_path, env="conanrun")
