#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test.

Consumer test for librecast/0.11.2: builds test.c against the packaged
headers/lib and runs it on the target (OHOS device). test.c makes real
librecast API calls (context / channel / socketpair lifecycle) with
observable assertions — no multicast networking required.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibrecastTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # librecast.h 间接包含 <sodium.h>，test_package 需显式获取其 include 路径
        self.requires("libsodium/1.0.22")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # HMDFS 上 cmake 产物位于 build/<generator-triplet>/test_librecast，
            # cpp.build.bindirs 在 test 阶段可能解析为 "."，用 glob 兜底定位
            hits = glob.glob(os.path.join(self.build_folder, "**", "test_librecast"), recursive=True)
            assert hits, "test_librecast binary not found in build folder"
            self.run(hits[0], env="conanrun")
