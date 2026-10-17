#!/usr/bin/env python3
"""Conan test_package — xcb-util-renderutil 0.3.10 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XcbUtilRenderutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # xcb_renderutil.h includes <xcb/render.h> from libxcb.
        # CMakeDeps only generates targets for directly-required packages,
        # so we require libxcb/1.17.0 explicitly in the test.
        self.requires("libxcb/1.17.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_xcb_util_renderutil")
        self.run(test_bin, env="conanrun")
