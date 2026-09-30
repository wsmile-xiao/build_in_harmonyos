#!/usr/bin/env python3
"""Conan consumer test for the libcompface API and command-line tools."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibcompfaceTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info(
                "Skipping runtime consumer test: host executable cannot run on the build machine"
            )
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libcompface")
        package_dir = self.dependencies["libcompface"].package_folder
        compface_bin = os.path.join(package_dir, "bin", "compface")
        uncompface_bin = os.path.join(package_dir, "bin", "uncompface")
        command = " ".join(
            shlex.quote(path)
            for path in (test_bin, compface_bin, uncompface_bin)
        )
        self.run(command, env="conanrun")
