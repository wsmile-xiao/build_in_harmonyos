#!/usr/bin/env python3
"""Conan test_package — consumer test for coin3 4.0.7.

Builds a small consumer executable that initializes the Coin database, builds
an Inventor scene graph and writes it back to a buffer, asserting the output
contains the 'Cube' node (real public API usage with observable result).

Runtime notes (OHOS): the binary dynamically links gl4es' libGL.so (our GL
provider). ctest does not propagate the Conan run environment, so we execute
the consumer explicitly with env='conanrun' (VirtualRunEnv) and point gl4es
at the device's real GLES/EGL libs via LIBGL_GLES/LIBGL_EGL.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Coin3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # Run the consumer explicitly with the Conan run environment
        # (VirtualRunEnv) so gl4es' libGL.so is found at runtime, and point
        # gl4es at the device's real GLES/EGL libraries. ctest does not
        # propagate these env vars (the binary segfaults without them), so we
        # do NOT use cmake.test() here. VirtualRunEnv only adds the gl4es lib
        # dir; the coin3 package's own lib dir (for libCoin.so.80) must be
        # prepended manually.
        coin3_lib = os.path.join(self.dependencies["coin3"].package_folder, "lib")
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_coin3")
        self.run(
            "LIBGL_GLES=/system/lib64/libGLESv3.so "
            "LIBGL_EGL=/system/lib64/libEGL.so "
            f'LD_LIBRARY_PATH="{coin3_lib}:$LD_LIBRARY_PATH" ' +
            f'"{binpath}"',
            env="conanrun",
        )