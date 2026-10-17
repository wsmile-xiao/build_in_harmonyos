#!/usr/bin/env python3
"""Conan test_package for mruby 3.3.0.

R34: Test must substantively depend on the tested package.
This test compiles a C program that uses the mruby C API
(mrb_open + mrb_load_string) and verifies the result.
Also runs the mruby binary from the package to verify it works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MrubyTestConan(ConanFile):
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
        # Run the compiled test binary that uses mruby C API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mruby")
        self.run(test_bin, env="conanrun")
        # Also verify the mruby binary from the package works
        dep = self.dependencies["mruby"]
        mruby_bin = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "mruby")
        self.run(f'"{mruby_bin}" --version', env="conanrun")
