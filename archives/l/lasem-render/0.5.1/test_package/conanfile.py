#!/usr/bin/env python3
"""Conan test_package — lasem-render 0.5.1 (L1 consumer test).

Builds test_lasem_render.c against the installed lasem package via CMakeDeps
and runs it with the conanrun environment: the binary parses an inline
MathML document, performs layout (pango text shaping) and renders onto a
cairo ARGB32 surface, then tears the library down with lsm_shutdown().
Exit code 0 == consumer verification PASS.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LasemRenderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly with the conanrun environment: the
        # renderer needs the shared deps (glib/cairo/pango/fontconfig .so)
        # on LD_LIBRARY_PATH — ctest/plain execution lacks them and cairo
        # fails early (status 32, "Cannot load default config file").
        exe = os.path.join(self.cpp.build.bindirs[0], "test_lasem_render")
        self.run(f'"{exe}"', env="conanrun")
