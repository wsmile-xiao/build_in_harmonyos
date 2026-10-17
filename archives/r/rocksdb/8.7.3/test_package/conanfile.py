#!/usr/bin/env python3
"""Test package for rocksdb 8.7.3."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.build import cross_building


class RocksdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Ninja generator: `/bin/sh` is not usable by the default Unix Makefiles
        # generator in the OHOS container, so use Ninja which execs commands
        # directly.
        CMakeToolchain(self, generator="Ninja").generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_rocksdb"), env="conanrun")
