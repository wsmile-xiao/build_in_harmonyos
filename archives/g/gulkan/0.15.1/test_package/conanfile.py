#!/usr/bin/env python3
"""Conan test_package for gulkan 0.15.1 — executes the real API (R34)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.layout import basic_layout


class GulkanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Absolute path: basic_layout puts the exe in the build folder root
        # and self.run's cwd is NOT that dir (relative bare names -> sh 127).
        exe = os.path.abspath(os.path.join(self.build_folder, "gulkan_test"))
        if not os.path.isfile(exe):
            exe = os.path.abspath(
                os.path.join(self.cpp.build.bindir, "gulkan_test"))
        # VirtualRunEnv (aggregated at generate()) exports LD_LIBRARY_PATH for
        # gulkan + its full shared-dep chain (glib/gobject/gdk-pixbuf/cairo/
        # pixman/graphene/tiff/jpeg/fontconfig/freetype/...).
        self.run(f'"{exe}"', env="conanrun")
