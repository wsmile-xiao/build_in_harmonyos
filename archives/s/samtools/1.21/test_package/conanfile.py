#!/usr/bin/env python3
"""Conan test_package — samtools 1.21.

Compiles and runs a C test that verifies the samtools binary
is installed and can report its version correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class SamtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = configured.get("c")
        build_env = Environment()
        if compiler:
            toolchain_lib = os.path.realpath(
                os.path.join(os.path.dirname(compiler), os.pardir, "lib")
            )
            if os.path.isdir(toolchain_lib):
                build_env.prepend_path("LD_LIBRARY_PATH", toolchain_lib)
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        # Run the compiled test binary
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_samtools")
        samtools_bin = os.path.join(
            self.dependencies["samtools"].cpp_info.bindirs[0], "samtools")
        self.run(f'"{bin_path}" "{samtools_bin}"', env="conanrun")
