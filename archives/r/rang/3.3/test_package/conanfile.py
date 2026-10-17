#!/usr/bin/env python3
"""Conan test_package for rang 3.3 — consumer-side verification of the header-only library.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RangTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile carries os.version; the header-only test needs no
        # version-specific packaging ID (matches repo mdurl/afdko pattern).
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS: CMake does not know the OHOS platform; the rang header only
        # needs POSIX/unistd.h, so map to Linux (repo range-v3 pattern).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # The OHOS clang 15 only ships libc++; force it explicitly.
            tc.extra_cxxflags.append("-stdlib=libc++")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_rang"), env="conanrun")
