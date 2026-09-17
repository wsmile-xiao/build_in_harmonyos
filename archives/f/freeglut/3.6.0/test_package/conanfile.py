#!/usr/bin/env python3
"""Test package for freeglut 3.6.0 — consumer compile/link + REAL execution.

The host running this test is the HarmonyOS aarch64 device itself, so the test
binary is executed (R34) rather than merely built.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FreeglutTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv: the test binary's NEEDED entries are sonames without RUNPATH,
    # so the library search path must come from the conanrun environment.
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_freeglut")
        if can_run(self):
            self.run(exe, env="conanrun")
        else:
            self.output.warning(
                f"cannot run {exe} on this host -- falling back to existence check")
            if not os.path.isfile(exe):
                raise ConanException(f"test binary not built: {exe}")
