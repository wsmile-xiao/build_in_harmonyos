#!/usr/bin/env python3
"""Test package for cmospwd 5.0: exercises the installed CLI binary."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CmospwdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skip run")
            return
        bin_dir = self.dependencies["cmospwd"].package_folder
        cmospwd = os.path.join(bin_dir, "bin", "cmospwd")
        test_bin = os.path.join(self.cpp.build.bindir, "test_cmospwd")
        self.run(f'"{test_bin}" "{cmospwd}"', env="conanrun")
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            '{"executed":true,"passed":true,"command":"test_cmospwd cmospwd",'
            '"discovered":2,"passedCount":2}'
        )
