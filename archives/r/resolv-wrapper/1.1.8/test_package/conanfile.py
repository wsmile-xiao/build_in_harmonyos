#!/usr/bin/env python3
"""Conan L1 consumer test — build a small binary that links and runs against
libresolv_wrapper's public API (res_ninit/res_nquery/res_nclose) and verifies
the DNS-faking path returns a parseable answer."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ResolvwrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # OHOS SDK CMake does not know "OHOS" as a platform; the profile's
            # OHOS-adapted toolchain expects plain Linux target (aarch64).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        exe = os.path.join(self.cpp.build.bindirs[0], "test_resolv-wrapper")
        # Note: test.c points RESOLV_WRAPPER_HOSTS at its own temp file and
        # calls the wrapper's public res_n* API directly (no external LD_PRELOAD
        # needed for the consumer path).
        self.run(exe, env="conanrun")
