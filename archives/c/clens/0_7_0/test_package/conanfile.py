#!/usr/bin/env python3
"""Conan test_package for clens 0_7_0 — consumer-side validation of the
OpenBSD-compat APIs the OHOS port actually ships (clens_verstring,
clens_version, strtonum, fmt_scaled/scan_scaled, fparseln) plus the
compat symbols that resolve from OHOS libc instead of libclens.a
(strlcpy/strlcat, arc4random_uniform, glob)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ClensTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_clens"),
                 env="conanrun")
