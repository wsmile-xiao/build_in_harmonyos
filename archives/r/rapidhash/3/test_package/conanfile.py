#!/usr/bin/env python3
"""Conan test_package for rapidhash/3 — real consumer build + run.

Builds three consumers against the packaged header (find_package(rapidhash)
+ rapidhash::rapidhash) and runs them via self.run(..., env="conanrun"):
  - test_rapidhash        (C99)  frozen KAT vectors + property assertions
  - test_rapidhash_cpp   (C++17) same KAT + std::string/std::vector paths
  - ohos_platform_test   (C++17) HarmonyOS platform-specific checks
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RapidhashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile carries os.version; the header-only test needs no
        # version-specific package id (repo mdurl/afdko/rang pattern).
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS: CMake does not know the OHOS platform; the headers only need
        # <stdint.h>/<string.h>, so map to Linux (repo rang/range-v3 pattern).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # OHOS clang 15 only ships libc++; force it explicitly.
            tc.extra_cxxflags.append("-stdlib=libc++")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_rapidhash"), env="conanrun")
        self.run(os.path.join(bindir, "test_rapidhash_cpp"), env="conanrun")
        self.run(os.path.join(bindir, "ohos_platform_test"), env="conanrun")
