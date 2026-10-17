#!/usr/bin/env python3
"""Conan consumer test for Google Benchmark 1.9.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BenchmarkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "test_package runtime checks were skipped because the target "
                "executable cannot run in the current cross-compilation environment"
            )
            return

        build_dir = self.build_folder
        api_test = os.path.join(build_dir, "test_benchmark")
        main_test = os.path.join(build_dir, "test_benchmark_main")
        self.run(
            f'"{api_test}" --benchmark_min_time=0.001s',
            env="conanrun",
        )
        self.run(
            f'"{main_test}" --benchmark_min_time=0.001s',
            env="conanrun",
        )
