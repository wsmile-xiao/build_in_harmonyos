#!/usr/bin/env python3
"""Conan test_package — vecgeom/1.2.8（Conan L1 消费者测试）。

真实链接并运行被测包：
  * test_vecgeom：调用 VecGeom 公开 API（Builder Box 的 Capacity/SurfaceArea/Inside/Extent）
  * test_ohos   ：鸿蒙特有用例，仅 OHOS 目标构建，验证 __OHOS__ 平台识别 + 运行时导航

PF3 前置门禁要求 test() 内有 self.run 实执行逻辑，此处两个用例都会真实运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VecgeomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 与主配方一致：OHOS 显式声明系统名，保证 CMAKE_SYSTEM_NAME=OHOS，
        # 从而 test_package/CMakeLists.txt 的 OHOS 分支（test_ohos）被构建。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        # L1：真实运行被测包（PF3 要求 self.run 实执行）
        self.run(os.path.join(bindir, "test_vecgeom"), env="conanrun")
        if self.settings.os == "OHOS":
            # 鸿蒙特有用例
            self.run(os.path.join(bindir, "test_ohos"), env="conanrun")
