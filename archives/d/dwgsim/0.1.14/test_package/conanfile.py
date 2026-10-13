#!/usr/bin/env python3
"""Conan test_package - dwgsim 0.1.14 CLI verification.

dwgsim is a command line tool with no library surface, so the consumer test
compiles a small driver that executes the installed `dwgsim` and `dwgsim_eval`
binaries end to end (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DwgsimTestConan(ConanFile):
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
        bindir = os.path.join(self.dependencies["dwgsim"].package_folder, "bin")
        dwgsim = os.path.join(bindir, "dwgsim")
        dwgsim_eval = os.path.join(bindir, "dwgsim_eval")
        test_bin = os.path.join(self.build_folder, "test_dwgsim")
        self.run('"%s" "%s" "%s"' % (test_bin, dwgsim, dwgsim_eval), env="conanrun")
