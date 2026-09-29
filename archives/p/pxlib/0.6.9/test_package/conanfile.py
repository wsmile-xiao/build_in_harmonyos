#!/usr/bin/env python3
"""Conan test_package for pxlib: compile and link against the packaged library."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PxlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindir = self.cpp.build.bindirs[0]
            self.run(os.path.join(bindir, "test_pxlib"), env="conanrun")
            # HarmonyOS PC native checks (OHOS toolchain identity,
            # read-only /tmp, $HOME/tmp scratch fallback).  Runs on the
            # OHOS target; a no-op SKIP on any other platform.
            self.run(os.path.join(bindir, "test_ohos"), env="conanrun")
