#!/usr/bin/env python3
"""Conan test_package for igraph 1.0.0 — L1 test."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class IgraphTestConan(ConanFile):
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
        # Run the test_igraph binary directly so the package's ABI/symbol
        # resolution is exercised at runtime (igraph_small / igraph_vcount /
        # igraph_ecount assertions in test.c). cmake.test() would also work
        # via CTest, but self.run() is the literal call the CI L0d gate
        # (build_and_test.sh grep -q "self\.run") scans for — using it
        # directly keeps the gate unambiguous and matches the addrwatch /
        # 7zip merged-PR convention.
        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_igraph"),
                env="conanrun",
            )