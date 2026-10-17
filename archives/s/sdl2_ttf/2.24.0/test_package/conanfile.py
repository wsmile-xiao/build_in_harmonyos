#!/usr/bin/env python3
"""Conan test_package — sdl2_ttf 2.24.0 consumer-side functional test.

Upstream ships no automated test suite (ctest/make check). The interactive
sample programs (showfont.c, glfont.c) require a display + font file and
cannot run in headless CI. This test_package provides a headless functional
test that exercises the TTF API lifecycle (init/version/query/quit).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Sdl2TtfTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        # Run all three tests: API lifecycle + version consistency + OHOS-specific
        for test_bin in ("test_sdl2_ttf", "test_version", "test_ohos"):
            self.run(os.path.join(bindir, test_bin), env="conanrun")
