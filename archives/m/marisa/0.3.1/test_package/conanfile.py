#!/usr/bin/env python3
"""Conan test_package for marisa 0.3.1 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is driven by the
Conan toolchain, not raw shell env vars (R33). The consumer test builds a
trie, round-trips it through save/load, and exercises lookup /
predictive_search / common_prefix_search / reverse_lookup.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MarisaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R5: OHOS has no /bin/sh — wrap binary execution with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_marisa'", env="conanrun")
