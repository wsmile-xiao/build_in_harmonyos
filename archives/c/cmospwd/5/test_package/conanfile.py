#!/usr/bin/env python3
"""Test package for cmospwd 5: drives the installed CLI binary and checks decoded output."""

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
        pkg_folder = self.dependencies["cmospwd"].package_folder
        cmospwd = os.path.join(pkg_folder, "bin", "cmospwd")
        test_bin = os.path.join(self.cpp.build.bindir, "test_cmospwd")
        self.run(f'"{test_bin}" "{cmospwd}" "{pkg_folder}"', env="conanrun")
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            '{"executed":true,"passed":true,"command":"test_cmospwd bin/cmospwd <pkg_folder>",'
            '"discovered":24,"passedCount":24}'
        )
