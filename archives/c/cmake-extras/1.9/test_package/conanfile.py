#!/usr/bin/env python3
"""Conan test_package for cmake-extras — runs the R34 consumer check.

L1 official test: runs a Python script that verifies the packaged CMake
modules exist under <pkg>/share/cmake/ (CopyrightTest, GDbus, GSettings,
Intltool, Vala, etc.) — the modules a consuming CMake project would
find_package()/include(). R34 real artifact verification.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["cmake-extras"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_cmake_extras.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
