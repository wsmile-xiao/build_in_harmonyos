#!/usr/bin/env python3
"""Conan consumer tests for qwprot on HarmonyOS aarch64."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class QwprotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if not can_run(self):
            return

        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_qwprot"), env="conanrun")
        self.run(os.path.join(bindir, "test_qwprot_ohos"), env="conanrun")
