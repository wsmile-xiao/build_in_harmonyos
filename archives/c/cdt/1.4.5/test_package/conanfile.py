#!/usr/bin/env python3
"""Conan test_package — cdt 1.4.5 消费者验证 (C++ header-only).

真实调用被测库 CDT 公开 API（约束 Delaunay 三角剖分）：
- 插入顶点与约束边 -> 校验拓扑 (verifyTopology)
- 擦除超三角形 -> 断言三角网非空
- 鸿蒙专项测试：int64 索引类型实例化 + 多批次插入 + 显式断言
非空壳测试（R34/PF3 合规）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CdtTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

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
            # 消费者验证：真实链接 header-only 库并执行三角剖分
            self.run(os.path.join(self.cpp.build.bindir, "test_cdt"), env="conanrun")
            # HarmonyOS 专项测试：独立可执行 target，单独运行（与 test_package 分离）
            self.run(os.path.join(self.cpp.build.bindir, "ohos_specific_test"), env="conanrun")