#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test.

Consumer test for lcrq/0.4.1: builds test.c against the packaged
headers/lib and runs it on the target (OHOS device). test.c makes real
lcrq API calls (RaptorQ encode/decode round-trip) with observable
assertions.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LcrqTestConan(ConanFile):
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
        if can_run(self):
            # HMDFS 上 cmake 产物位于 build/<generator-triplet>/test_lcrq，
            # cpp.build.bindirs 在 test 阶段可能解析为 "."，用 glob 兜底定位
            hits = glob.glob(os.path.join(self.build_folder, "**", "test_lcrq"), recursive=True)
            assert hits, "test_lcrq binary not found in build folder"
            self.run(hits[0], env="conanrun")
