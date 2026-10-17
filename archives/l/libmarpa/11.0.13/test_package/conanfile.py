#!/usr/bin/env python3
"""Conan test_package for libmarpa 11.0.13 — consumer link/run test (R34).

Builds a real grammar with the public marpa.h API (version contract, symbols,
rules, precompute, recognition, bocage/order/tree/value steps) via CMake,
links against the packaged library, and runs it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmarpaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # spawn the test through bash from PATH (the HNP bash full path is
        # not stable across hosts).
        self.run('bash -c "./libmarpa_test"', env="conanrun")
