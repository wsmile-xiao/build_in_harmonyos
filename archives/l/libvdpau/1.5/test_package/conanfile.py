#!/usr/bin/env python3
"""Conan test_package for libvdpau 1.5.

Links against the real libvdpau.so and drives the wrapper's dlopen()
dispatch path (see test.c). CI L1e negative test: removing the package
lib/ must break this build/link, proving genuine dependence.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibvdpauTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeDeps/CMakeToolchain declared via generators; runtime env for
        # the shared library lookup (conanrun defines LD_LIBRARY_PATH).
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libvdpau")
        self.run(test_bin, env="conanrun")
