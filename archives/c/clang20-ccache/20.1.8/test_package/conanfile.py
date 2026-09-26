#!/usr/bin/env python3
"""Conan test_package — clang20-ccache 20.1.8

L1 smoke test: builds and runs test.c which invokes the installed `ccache`
binary (`ccache --version`) and asserts exit code 0 + version 4.14 (R34).
clang20-ccache is a CLI tool package (no library API), so the test does NOT
link any package library target — it executes the packaged binary via PATH.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CcacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: actually execute the packaged ccache binary and assert it runs
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "ccache --version | head -1"', env="conanrun")
        # L0d + R34: run the compiled test binary that invokes ccache --version
        #            and asserts exit code 0 + version 4.14
        cmake = CMake(self)
        cmake.ctest(env="conanrun")