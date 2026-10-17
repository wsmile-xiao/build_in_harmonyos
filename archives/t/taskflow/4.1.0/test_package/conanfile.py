#!/usr/bin/env python3
"""test_package — builds and runs a real C++20 consumer of taskflow 4.1.0.

The consumer uses the installed headers only (no upstream source tree) and
checks observable results: work-stealing executor, taskflow graph with
precede() edges, parallel for_each/reduce results, and repeated large-graph
churn that exercises the tf::ObjectPool cold path adapted for OHOS.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TaskflowTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # cmake_layout keeps the built binary and the generated env scripts
        # out of the package source directory.
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            consumer = os.path.join(self.cpp.build.bindirs[0], "consumer")
            self.run(f'"{consumer}"', env="conanrun")
