#!/usr/bin/env python3
"""Conan test_package — clove-unit 2.4.6 的 L2 消费者测试。

两个可执行文件（见 CMakeLists.txt）：
  * test_clove_unit    —— 消费者冒烟：3 用例 / 8 断言，直接 `#include <clove-unit.h>`
                          （来自 conan 包的 include/），进程退出码即用例结果；
  * ohos_special_test  —— 鸿蒙专项：16 项端到端断言（自动发现 / 报告格式 /
                          过滤语义 / 自报版本），在 OHOS aarch64 上真实执行。
test_package 合计 24 条断言。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CloveUnitTestPackageConan(ConanFile):
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
        # 沙箱 HOME：不在用户真实 HOME 下执行测试（AGENTS §2 / §3.5）
        sandbox = os.path.join(str(self.build_folder), "clove-test-home")
        os.makedirs(sandbox, exist_ok=True)
        # 先打注册清单：日志里必须能看到 `Total Tests: 2`（ctest 0 注册时 rc=0，
        # 属结构性假绿，须有正向证据再采信）。
        self.run("HOME=%s ctest -N" % sandbox, cwd=str(self.build_folder))
        self.run("HOME=%s ctest --output-on-failure" % sandbox, cwd=str(self.build_folder))
