#!/usr/bin/env python3
"""Conan test_package for lcmaps 1.6.7 — OHOS consumer smoke verification.

Builds test_lcmaps (C, dlopen-based) against the packaged headers and runs it
with the package root as argument. See test.c for the covered adaptation points.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LcmapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = self.dependencies["lcmaps"]
        tc = CMakeToolchain(self)
        tc.variables["LCMAPS_TEST_ROOT"] = deps.package_folder
        tc.variables["LCMAPS_TEST_INCDIR"] = os.path.join(
            deps.package_folder, "include"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lcmaps")
        pkg_path = self.dependencies["lcmaps"].package_folder
        self.run("'%s' '%s'" % (bin_path, pkg_path), env="conanrun")
