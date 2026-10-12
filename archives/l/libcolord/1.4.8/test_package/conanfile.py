#!/usr/bin/env python3
"""Conan test_package — libcolord L1 consumer test.

Verifies libcolord client library API (CdColorRGB and CdIcc) is usable
from a downstream project built with CMakeDeps.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibcolordTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib2 is a transitive dep of libcolord; declare it explicitly so the
        # test source (which uses g_object_unref / g_strcmp0) gets its headers.
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_libcolord")
            self.run(bin_path, env="conanrun")
