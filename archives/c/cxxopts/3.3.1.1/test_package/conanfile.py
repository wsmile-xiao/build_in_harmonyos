#!/usr/bin/env python3
"""cxxopts test_package — 消费者用例：模拟上层组件调用 cxxopts 公开 API."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class CxxoptsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        if can_run(self):
            import os
            binary = os.path.join(self.build_folder, "test_cxxopts")
            self.run(f"{binary} -n harmonyos", env="conanrun")
