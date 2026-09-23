#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for kdtree.

Creates a kd-tree, inserts points, runs a nearest-neighbor query and
verifies an observable result through the public kdtree.h API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KdtreeTestConan(ConanFile):
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
        # L0d/R34: must actually execute the tested binaries via self.run.
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_kdtree"), env="conanrun")
        self.run(os.path.join(bindir, "test_kdtree_ohos"), env="conanrun")
