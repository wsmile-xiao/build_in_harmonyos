#!/usr/bin/env python3
"""Consumer tests for the installed TLFloat package on HarmonyOS."""

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout


class TlfloatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("Cross-building: compiled and linked consumer test")
            return
        cmake = CMake(self)
        cmake.test()
        bindir = self.cpp.build.bindirs[0]
        self.run(f'"{bindir}/test_tlfloat"', env="conanrun")
        self.run(f'"{bindir}/tlfloat_consumer_workflow"', env="conanrun")
