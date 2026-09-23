#!/usr/bin/env python3
"""Conan test_package — Dawn L1 consumer test.

Builds a small C consumer that calls wgpuCreateInstance/wgpuInstanceRelease
against the installed dawn library (webgpu_dawn bundled static library).
webgpu_dawn bundles only Dawn's own objects, so the consumer also links the
ohpcd abseil static libraries for the symbols Dawn references.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DawnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # webgpu_dawn bundles Dawn objects only; link the ohpcd abseil
        # package for the abseil symbols Dawn references.
        self.requires("abseil/20260526")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        abseil = self.dependencies["abseil"]
        tc.variables["ABSEIL_LIB_DIR"] = os.path.join(
            abseil.package_folder, "lib").replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d: CI 要求 test() 内含 self.run 实际执行逻辑（禁止空壳）。
        # 直接运行消费者测试二进制 (wgpuCreateInstance/Release 真实调用)。
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_dawn")
        self.run(bin_path, env="conanrun")
