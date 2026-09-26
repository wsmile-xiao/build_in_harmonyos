#!/usr/bin/env python3
"""Conan test_package for rinutils 0.10.3.

Consumer-side verification: builds test_rinutils against the packaged headers
found via CMakeDeps (`find_package(Rinutils)` + `Rinutils::Rinutils`) and runs
it. test.c exercises every installed header (count / min_and_max / str_utils /
alloc_wrap / bit_rw / longlong / portable_time / likely / typeof_wrap / unused /
dllexport / rinutils aggregate) with positive and negative controls; CHECK()
keeps assertions active in Release (-DNDEBUG).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RinutilsTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d/PF3: explicitly run the tested binary (not a print-only shell).
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_rinutils"), env="conanrun")
