#!/usr/bin/env python3
"""Conan test_package — tigr 3.1.0.

L1 消费者测试（R34）：真实调用被测包公开 API 并校验可观察结果。
本测试在 TIGR_HEADLESS 模式下运行：创建位图 → 绘制原语 → 渲染文字 →
保存 PNG → 重新加载 → 逐像素校验，全程无需窗口/显示服务器。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TigrTestConan(ConanFile):
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
        # 直接运行二进制（headless，无窗口）：消费者测试 + 鸿蒙专项测试
        bin_dir = self.cpp.build.bindirs[0]
        for exe in ("test_tigr", "test_tigr_ohos"):
            self.run(os.path.join(bin_dir, exe), env="conanrun")
