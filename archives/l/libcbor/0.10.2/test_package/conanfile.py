#!/usr/bin/env python3
"""Conan test_package for libcbor 0.10.2.

Builds and runs two consumer executables against the packaged libcbor:
  - test_libcbor: uint/string/array CBOR encode-decode round-trip
  - ohos_special_test: HarmonyOS-specific checks (wide ints, large bytestring,
    nested map/array, streaming decode)
Both use CHECK() macros so assertions execute even under Release (-DNDEBUG).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibcborTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 显式运行被测二进制（防空壳，R34/PF3）
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_libcbor"), env="conanrun")
        self.run(os.path.join(bin_dir, "ohos_special_test"), env="conanrun")
