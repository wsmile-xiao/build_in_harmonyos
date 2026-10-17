#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libsvgtiny/0.1.8/test_package/conanfile.py

In addition to the consumer smoke test (test_svgtiny), the vendored upstream
test harness (upstream/decode_svg.c, the same binary `make test` drives) is
built and run by CTest against the vendored upstream data files
(upstream/data/*.svg, one case per file). This is the rule4 "实跑上游测试"
requirement.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsvgtinyTestConan(ConanFile):
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
        # CTest runs test_svgtiny (consumer smoke test) plus one decode_* case
        # per vendored upstream data file (12 cases, runtest.sh exit-0
        # semantics). See CMakeLists.txt for the registration.
        cmake = CMake(self)
        cmake.test()

        # L0d gate requires an explicit self.run() in test(): also run the
        # consumer smoke test binary directly.
        bin_dir = self.cpp.build.bindirs[0]
        self.run(f'"{os.path.join(bin_dir, "test_svgtiny")}"')
