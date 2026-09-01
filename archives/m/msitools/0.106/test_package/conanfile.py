#!/usr/bin/env python3
"""Conan test_package — msitools 0.106 L1 test.

Tests that the msitools package can be linked and the MSI API is usable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MsitoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # lld enables --no-allow-shlib-undefined by default; override it
        # (libgsf.so has transitive deps on libintl not in the link line)
        if str(self.settings.os) == "OHOS":
            tc.extra_exelinkflags.append("-Wl,--allow-shlib-undefined")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Collect all dependency lib dirs for LD_LIBRARY_PATH
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        new_ld = os.pathsep.join(lib_dirs)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_msitools")
        self.run(f'LD_LIBRARY_PATH="{new_ld}" "{bin_path}"')
