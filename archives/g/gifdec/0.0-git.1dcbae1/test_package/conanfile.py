#!/usr/bin/env python3
"""Conan test_package for gifdec 0.0-git.1dcbae1 — Conan L1 consumer test.

gifdec upstream ships no test suite (example.c is an interactive SDL2
player, not a test). This consumer suite links against the packaged
static library + installed header and programmatically synthesizes
minimal GIF89a byte streams (header + LSD + 2-entry GCT + image
descriptor + hand-packed LSB-first LZW data), writes them to a temp
directory and drives the full public API: gd_open_gif / gd_get_frame /
gd_render_frame / gd_is_bgcolor / gd_rewind / gd_close_gif.

All assertion anchors were calibrated on the target (OHOS aarch64,
clang 15) against unmodified upstream gifdec.c before freezing.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GifdecTestConan(ConanFile):
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
        # Create the writable dir for synthesized GIF files BEFORE
        # cmake.test() — the add_test COMMAND points into it (fopen for
        # write would fail on a missing dir and false-fail ctest)
        tmp_dir = os.path.join(self.build_folder, "gif-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        cmake = CMake(self)
        # plain invocation: cli_args are cmake-side flags, not ctest flags
        cmake.test()
        # Also run the consumer test binary directly (L1b log evidence)
        self.run(
            f'{os.path.join(self.cpp.build.bindirs[0], "test_gifdec")} "{tmp_dir}"',
            env="conanrun",
        )
