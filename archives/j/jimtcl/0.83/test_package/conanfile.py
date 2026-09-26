#!/usr/bin/env python3
"""Conan test_package — jimtcl 0.83 consumer verification (CI L1).

Two real consumer paths, both asserting packaged behaviour:
  1. build() compiles test.c against jimtcl::jimtcl (CMakeDeps) — links the
     packaged libjim.a + conan zlib, embeds an interpreter.
  2. test() runs the packaged bin/jimsh on test.tcl.
Counts (7 + 5 = 12 assertions) feed the PR body's 鸿蒙特有测试 row.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JimtclTestConan(ConanFile):
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
        # 1) consumer binary linking the packaged libjim
        exe = os.path.join(self.cpp.build.bindirs[0], "test_jimtcl")
        self.run(exe, env="conanrun")
        # 2) packaged jimsh driving a Tcl script
        dep = self.dependencies["jimtcl"]
        jimsh = os.path.join(dep.package_folder, "bin", "jimsh")
        script = os.path.join(self.source_folder, "test.tcl")
        self.run(f'"{jimsh}" "{script}"', env="conanrun")
