#!/usr/bin/env python3
"""Conan test_package — devio 1.2 L1 test.

L1 test: cmake 编译 test_devio.c（host=aarch64）→ test() 阶段
cross_building 跳过本地执行（devio 是 aarch64 ELF，Windows x86
host 跑不了），CI 阶段由 ohpcd 真机/模拟器执行 binary 校验。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class DevioTestConan(ConanFile):
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
        if cross_building(self):
            # devio 是 aarch64 ELF，Windows x86 host 跑不了
            # CI 端由 ohpcd 真机/模拟器执行 binary 校验（--help 输出检查）
            self.output.info(
                "cross-building: devio binary checks deferred to OHOS runtime")
            return
        # native build（开发者自测）：执行 test_devio 验证 binary 可执行 + --help
        devio_bin = os.path.join(
            self.dependencies["devio"].package_folder, "bin", "devio")
        test_exe = os.path.join(self.cpp.build.bindir, "test_devio")
        self.run(f"{test_exe} {devio_bin}")
