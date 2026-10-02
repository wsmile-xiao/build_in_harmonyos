#!/usr/bin/env python3
"""Conan test_package — open-dis-cpp 1.0.1 (CMake 消费者)"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OpenDisCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        # 3 个消费者用例：test_dis6_roundtrip / test_dis7_roundtrip / test_ohos_runtime
        self.run("ctest --output-on-failure --no-tests=error",
                 cwd=self.build_folder, env="conanrun")
