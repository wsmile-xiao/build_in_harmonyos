#!/usr/bin/env python3
"""Conan test_package for aws-c-auth 0.10.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AwsCAuthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise RuntimeError("test_aws_c_auth executable directory was not produced")
            test_bin = os.path.join(bindirs[0], "test_aws_c_auth")
            for mode in ("--init", "--credentials"):
                self.run(f'"{test_bin}" {mode}', env="conanrun")
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")
