#!/usr/bin/env python3
"""Conan test_package — lwjson 1.9.0 L1 consumer test.

Consumers use only the installed public headers and the exported static
library via CMakeDeps (find_package(lwjson) -> lwjson::lwjson).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LwjsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: explicit self.run() execution (not just cmake.test()) — runs
        # the two registered ctest entries: test_lwjson (consumer) and
        # test_ohos (HarmonyOS/aarch64 specialty test).
        self.run("ctest --test-dir . --output-on-failure",
                 cwd=self.build_folder, env="conanrun")