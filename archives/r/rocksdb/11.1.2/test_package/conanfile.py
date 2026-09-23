#!/usr/bin/env python3
"""Conan test_package for rocksdb 11.1.2 — L1 consumer test.

Builds a real consumer program against the packaged RocksDB and runs it
natively on the OHOS device via ctest.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RocksdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def configure(self):
        # rocksdb 11.1.2 requires C++20 (its public headers use C++20
        # language/library features); the farm profile defaults to cppstd=17.
        self.settings.compiler.cppstd = "20"

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
        # CI gate: test() must execute the consumer binary through a real
        # self.run() step, not only cmake.test().
        binary = os.path.join(self.cpp.build.bindirs[0], "test_rocksdb")
        self.run(binary, env="conanrun")
