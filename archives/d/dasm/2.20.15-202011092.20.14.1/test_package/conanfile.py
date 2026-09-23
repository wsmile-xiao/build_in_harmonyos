#!/usr/bin/env python3
"""Conan test_package — dasm 消费者测试（CMake 构建 + 上游回归用例逐字节比对）。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DasmTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("cross-building: dasm runtime checks deferred to OHOS runner")
            return
        pkg = self.dependencies["dasm"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_dasm")
        # cwd 显式设为构建目录：测试会在 cwd 落地 .asm/.bin/.hex
        # （OHOS 上 /tmp 只读，不能写临时目录）。
        self.run(f'"{exe}" "{pkg}"', cwd=self.build_folder)
