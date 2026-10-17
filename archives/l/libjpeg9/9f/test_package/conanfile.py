#!/usr/bin/env python3
"""Conan test_package — libjpeg9 L1 consumer test + OHOS-specific (R26)
static-only package constraint test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Libjpeg9TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Inject the tested package lib dir so the OHOS-specific test can
        # assert the R26 static-only artifact layout against the real
        # package folder this consumer links against.
        dep = self.dependencies[self.tested_reference_str]
        lib_dir = os.path.join(dep.package_folder or "", "lib")
        tc.variables["LIBJPEG9_PKG_LIBDIR"] = lib_dir.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libjpeg9")
        self.run(bin_path, env="conanrun")
        # OHOS-only R26 static-constraint test; runs after the generic
        # consumer round-trip test on the device.
        if self.settings.os == "OHOS":
            ohos_bin = os.path.join(self.cpp.build.bindirs[0], "test_ohos_static")
            self.run(ohos_bin, env="conanrun")
        else:
            print("test_ohos_static skipped: OHOS-only test, os=" + str(self.settings.os))
