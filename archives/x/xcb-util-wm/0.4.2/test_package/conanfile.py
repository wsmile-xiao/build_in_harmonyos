#!/usr/bin/env python3
"""Conan test_package — xcb-util-wm 0.4.2 consumer link + real API test."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XcbUtilWmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The test source includes <xcb/xcb.h> and <xcb/xcb_icccm.h>; CMakeDeps
        # only exposes include paths of directly required packages.
        self.requires("libxcb/1.17.0")
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Execute the assertions through ctest (a test that is only compiled
        # verifies nothing), wrapped in the conanrun environment: the OHOS
        # loader ignores DT_RUNPATH, so the dependency lib directories must come
        # from LD_LIBRARY_PATH or the binary never runs an assertion.
        self.run(
            f'ctest --test-dir "{self.build_folder}" --output-on-failure',
            env="conanrun",
        )
