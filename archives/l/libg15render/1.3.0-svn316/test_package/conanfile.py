#!/usr/bin/env python3
"""Consumer tests for libg15render 1.3.0-svn316."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Libg15renderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        package_folder = self.dependencies["libg15render"].package_folder
        font_dir = os.path.join(package_folder, "share", "g15tools", "fonts")
        test_dir = self.cpp.build.bindir
        self.run(
            f"{shlex.quote(os.path.join(test_dir, 'test_libg15render'))} "
            f"{shlex.quote(font_dir)}",
            env="conanrun",
        )
        self.run(
            shlex.quote(os.path.join(test_dir, "test_libg15render_ohos")),
            env="conanrun",
        )
        converter = os.path.join(package_folder, "bin", "g15fontconvert")
        self.run(f"{shlex.quote(converter)} --help", env="conanrun")
        self.run(f"{shlex.quote(converter)} --version", env="conanrun")
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT(discovered=2, executed=2, "
            "passed=2, failed=0, skipped=0, suite=g15fontconvert_cli)"
        )
