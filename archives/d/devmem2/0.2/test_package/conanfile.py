#!/usr/bin/env python3
"""Conan test_package — devmem2 0.2 L1 test.

L1 test: cmake 编译 test_devmem2.c（host=aarch64）→ test() 阶段
cross_building 跳过本地执行（devmem2 是 aarch64 ELF，Windows x86
host 跑不了），CI 阶段由 ohpcd 真机/模拟器执行 binary 校验。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Devmem2TestConan(ConanFile):
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
            # devmem2 是 aarch64 ELF，Windows x86 host 跑不了
            # CI 端由 ohpcd 真机/模拟器执行 binary 校验（--version / --help 输出）
            self.output.info(
                "cross-building: devmem2 binary checks deferred to OHOS runtime")
            return
        # native build（开发者自测）：执行 test_devmem2 验证 binary 可执行 + --version
        devmem2_bin = os.path.join(
            self.dependencies["devmem2"].package_folder, "bin", "devmem2")
        test_exe = os.path.join(self.cpp.build.bindir, "test_devmem2")
        self.run(f"{test_exe} {devmem2_bin}")
