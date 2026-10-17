#!/usr/bin/env python3
"""Conan test_package — lzav 5.17 L1 consumer + HarmonyOS platform test.

Compiles real consumer programs that include the installed public header
`lzav.h` and exercise the public API (lzav_compress_default / lzav_decompress):
  - lzav_consumer_test: generic round-trip + malformed-input safety (R34)
  - lzav_ohos_test:      HarmonyOS runtime check (uname) + round-trip on OHOS
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LzavTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

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
            self.output.info("Skipping run: target binary cannot run here")
            return
        self.run("./lzav_consumer_test", env="conanrun")
        self.run("./lzav_ohos_test", env="conanrun")
