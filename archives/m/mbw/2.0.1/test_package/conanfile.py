#!/usr/bin/env python3
"""Conan test_package for mbw 2 — builds and runs a real test driver.

R34: the test must execute the packaged program and verify it works.
A small C driver (test.c) invokes the installed `mbw -n 1 1024` and
asserts rc==0 plus benchmark output markers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class MbwTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        self.run("./mbw_test", env="conanrun")
