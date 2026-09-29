#!/usr/bin/env python3
"""Conan test package - libinsane 1.0.10.

Links a real consumer against both exported libraries (core C API and the
GObject wrapper headers), pins the ABI with _Static_assert and exercises
lis_compare()/lis_getenv()/lis_free()/lis_get_version() plus the SANE device
surface, which must report the honest "no such device" failure on a machine
without a scanner. See test_libinsane.c and MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibinsaneTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

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
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindir, "test_libinsane")
            self.run(test_bin, env="conanrun")
