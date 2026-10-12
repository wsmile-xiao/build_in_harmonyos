#!/usr/bin/env python3
"""Conan test_package for nanosvg 0.0-git.239e102 — Conan L1 official test.

Consumer-perspective verification of BOTH shipped libraries (parser +
rasterizer): links against libnanosvg.a / libnanosvgrast.a via the
upstream CMake export (NanoSVG::nanosvg / NanoSVG::nanosvgrast), parses
an embedded minimal SVG string and asserts shape/path counts, geometry
bounds, paint defaults, and rasterizer coverage (all anchors measured
on the exact upstream snapshot).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NanosvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2 precedent).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # plain invocation: cli_args are cmake-side flags, not ctest flags
        cmake.test()
        # Also run the consumer test binary directly for L1b log evidence
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_nanosvg"),
            env="conanrun",
        )
