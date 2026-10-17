#!/usr/bin/env python3
"""Conan test_package — arg_router 1.3.0 消费者视角真实用例（L1 / R34 / PF3）。

消费者通过 CMakeDeps 的 ``arg_router::arg_router`` 目标链接**打包后的头文件**并
真实调用 arg_router 的公开 API（root/mode/flag/arg/default_value/validation）解析
argv；test_arg_router.cpp 任一断言失败 → 进程 rc != 0 → ``conan create`` 失败。

消费者断言数以运行期末行 ``ARG-ROUTER-CONSUMER checks=<N> failures=<M>`` 为准
（N=6，与 MANIFEST.yml 的 consumer_checks 一致），即 PR 正文「鸿蒙特有测试」行的取数。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ArgrouterTestConan(ConanFile):
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
            return
        # PF3/L0c：必须真实执行被测二进制（断言失败 rc != 0 即让本测试失败）
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_arg_router")
        self.run(cmd)
