#!/usr/bin/env python3
"""Conan test_package for libpipeline 1.5.8 — L1 consumer test.

libpipeline is a plain Autotools C library without a CMake package config,
so the consumer side uses pkg-config, which is how upstream consumers
(including dh-exec) find it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibpipelineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        PkgConfigDeps(self).generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The CI gate (门禁) requires test() to actually execute the consumer
        # binary through self.run(); a bare cmake.test() is rejected because the
        # runner cannot see a real execution step.
        cmake = CMake(self)
        cmake.test()
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libpipeline")
        self.run(exe, env="conanrun")
