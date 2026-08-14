#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test package for ATK — validates library linkage via atk_get_version() API call."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CI 真根因: atk 头 #include <glib-object.h> 但 test_package 只 requires atk →
        # CMakeDeps 不传播 glib 头路径致 glib-object.h not found（glib 头在 include/glib-2.0/）
        self.requires("glib/2.84.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(cmd, env="conanrun")
